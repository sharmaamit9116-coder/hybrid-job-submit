import os
import tempfile
import time
from typing import Dict, Optional

from ..errors import SubmissionError
from ..manifest import JobManifest
from ..utils import now_utc_iso, run_cmd, which


class SlurmBackend:
    def is_available(self) -> bool:
        return which("sbatch") is not None

    def submit(self, manifest: JobManifest, dry_run: bool = False) -> Dict:
        job_name = manifest.name or f"{manifest.team}-{manifest.user}-train"
        time_limit = self._slurm_time_limit(manifest.duration_hours)
        script = self._build_sbatch_script(manifest, job_name=job_name, time_limit=time_limit)

        if dry_run:
            return {
                "backend": "slurm",
                "job_id": "DRY_RUN",
                "expected_start_time": now_utc_iso(),
                "details": {"sbatch_script": script},
            }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sbatch", delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            rc, out, err = run_cmd(["sbatch", script_path])
            if rc != 0:
                raise SubmissionError(f"sbatch failed (rc={rc}): {err or out}")

            job_id = self._parse_job_id(out)
            if not job_id:
                raise SubmissionError(f"Could not parse Slurm job id from sbatch output: '{out}'")

            start = self._best_effort_start_time(job_id) or now_utc_iso()

            return {
                "backend": "slurm",
                "job_id": job_id,
                "expected_start_time": start,
                "details": {"sbatch_output": out},
            }
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

    @staticmethod
    def _slurm_time_limit(duration_hours: float) -> str:
        total_seconds = int(duration_hours * 3600)
        days = total_seconds // 86400
        rem = total_seconds % 86400
        hours = rem // 3600
        rem %= 3600
        minutes = rem // 60
        seconds = rem % 60
        if days > 0:
            return f"{days}-{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _parse_job_id(sbatch_output: str) -> Optional[str]:
        import re
        m = re.search(r"Submitted batch job\s+(\d+)", sbatch_output)
        return m.group(1) if m else None

    def _best_effort_start_time(self, job_id: str) -> Optional[str]:
        if which("squeue") is None:
            return None
        for _ in range(3):
            rc, out, err = run_cmd(["squeue", "-j", job_id, "-h", "-o", "%S"])
            if rc == 0 and out:
                return out.strip()
            time.sleep(1)
        return None

    @staticmethod
    def _build_sbatch_script(manifest: JobManifest, job_name: str, time_limit: str) -> str:
        qos = "high" if manifest.priority == "high" else "normal"
        gres = f"gpu:{manifest.gpus}"
        env_lines = "\n".join([f"export {k}={_shell_escape(v)}" for k, v in manifest.env.items()]) if manifest.env else ""

        return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err
#SBATCH --time={time_limit}
#SBATCH --gres={gres}
#SBATCH --qos={qos}
#SBATCH --account={manifest.team}

set -euo pipefail

{env_lines}

echo "Starting job on $(hostname) at $(date)"
cd {manifest.workdir}

# Container execution is environment-specific.
# If you have enroot/apptainer/singularity, plug it in here.
if command -v enroot >/dev/null 2>&1; then
  echo "Using enroot to run image: {manifest.image}"
  enroot start --rw {job_name} {manifest.command}
else
  echo "WARNING: enroot not found; running command on host."
  {manifest.command}
fi
""".rstrip() + "\n"


def _shell_escape(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"
