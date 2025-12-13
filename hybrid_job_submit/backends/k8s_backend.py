import hashlib
import json
import tempfile
from typing import Dict

from ..errors import SubmissionError
from ..manifest import JobManifest
from ..utils import now_utc_iso, run_cmd, which


class KubernetesBackend:
    def is_available(self) -> bool:
        return which("kubectl") is not None

    def submit(self, manifest: JobManifest, dry_run: bool = False) -> Dict:
        ns = manifest.namespace or manifest.team
        name = manifest.name or self._stable_name(manifest)

        if manifest.job_type == "inference":
            obj = self._build_inference_job(manifest, name=name, namespace=ns)
        elif manifest.job_type == "interactive":
            obj = self._build_interactive_pod(manifest, name=name, namespace=ns)
        else:
            raise ValueError(f"KubernetesBackend cannot handle job_type={manifest.job_type}")

        if dry_run:
            return {
                "backend": "kubernetes",
                "job_id": "DRY_RUN",
                "expected_start_time": now_utc_iso(),
                "details": {"namespace": ns, "manifest_object": obj},
            }

        self._ensure_namespace(ns)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json.dumps(obj, indent=2))
            path = f.name

        rc, out, err = run_cmd(["kubectl", "apply", "-f", path, "-n", ns])
        if rc != 0:
            raise SubmissionError(f"kubectl apply failed (rc={rc}): {err or out}")

        start = self._best_effort_start_time(manifest.job_type, name=name, namespace=ns) or now_utc_iso()

        return {
            "backend": "kubernetes",
            "job_id": name,
            "expected_start_time": start,
            "details": {"kubectl_apply": out, "namespace": ns},
        }

    def _ensure_namespace(self, ns: str) -> None:
        rc, out, err = run_cmd(["kubectl", "get", "ns", ns])
        if rc == 0:
            return
        run_cmd(["kubectl", "create", "ns", ns])

    def _best_effort_start_time(self, job_type: str, name: str, namespace: str):
        if job_type == "inference":
            rc, out, err = run_cmd(["kubectl", "get", "job", name, "-n", namespace, "-o", "jsonpath={.status.startTime}"])
            if rc == 0 and out:
                return out.strip()
        if job_type == "interactive":
            rc, out, err = run_cmd(["kubectl", "get", "pod", name, "-n", namespace, "-o", "jsonpath={.status.startTime}"])
            if rc == 0 and out:
                return out.strip()
        return None

    @staticmethod
    def _stable_name(manifest: JobManifest) -> str:
        h = hashlib.sha1(f"{manifest.team}|{manifest.user}|{manifest.job_type}|{manifest.command}".encode("utf-8")).hexdigest()[:8]
        return f"{manifest.team}-{manifest.job_type}-{h}"

    @staticmethod
    def _build_container(manifest: JobManifest) -> Dict:
        env = [{"name": k, "value": v} for k, v in (manifest.env or {}).items()]
        return {
            "name": "main",
            "image": manifest.image,
            "imagePullPolicy": "IfNotPresent",
            "command": ["/bin/bash", "-lc", manifest.command],
            "env": env,
            "resources": {
                "limits": {"nvidia.com/gpu": int(manifest.gpus)},
                "requests": {"nvidia.com/gpu": int(manifest.gpus)},
            },
            "volumeMounts": [{"name": "workspace", "mountPath": "/workspace"}],
            "workingDir": "/workspace",
        }

    def _build_inference_job(self, manifest: JobManifest, name: str, namespace: str) -> Dict:
        container = self._build_container(manifest)
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {"team": manifest.team, "job_type": "inference", "priority": manifest.priority},
            },
            "spec": {
                "backoffLimit": 0,
                "template": {
                    "metadata": {"labels": {"team": manifest.team, "job_type": "inference"}},
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [container],
                        "volumes": [{"name": "workspace", "emptyDir": {}}],
                    },
                },
            },
        }

    def _build_interactive_pod(self, manifest: JobManifest, name: str, namespace: str) -> Dict:
        container = self._build_container(manifest)
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {"team": manifest.team, "job_type": "interactive", "priority": manifest.priority},
                "annotations": {
                    "gpu.lenovo.com/sharing": "time-slicing",
                    "gpu.lenovo.com/interactive": "true",
                },
            },
            "spec": {
                "restartPolicy": "Never",
                "containers": [container],
                "volumes": [{"name": "workspace", "emptyDir": {}}],
            },
        }
