from typing import Dict

from .backends.k8s_backend import KubernetesBackend
from .backends.slurm_backend import SlurmBackend
from .errors import BackendDownError
from .manifest import JobManifest
from .quotas import enforce_quota


def route_and_submit(manifest: JobManifest, dry_run: bool = False) -> Dict:
    """Route based on job_type and submit to Slurm or Kubernetes."""
    enforce_quota(manifest.team, manifest.gpus)

    if manifest.job_type == "training":
        backend = SlurmBackend()
        if not backend.is_available():
            raise BackendDownError("Slurm backend appears down/unreachable (missing sbatch or no access).")
        return backend.submit(manifest, dry_run=dry_run)

    if manifest.job_type in {"inference", "interactive"}:
        backend = KubernetesBackend()
        if not backend.is_available():
            raise BackendDownError("Kubernetes backend appears down/unreachable (missing kubectl or no access).")
        return backend.submit(manifest, dry_run=dry_run)

    raise ValueError(f"Unsupported job_type: {manifest.job_type}")
