from dataclasses import dataclass, field
from typing import Dict, Optional

import yaml

from .errors import ManifestError


VALID_JOB_TYPES = {"training", "inference", "interactive"}
VALID_PRIORITIES = {"normal", "high"}


@dataclass
class JobManifest:
    team: str
    user: str
    job_type: str
    gpus: int
    duration_hours: float
    image: str
    priority: str
    command: str

    # Optional
    name: Optional[str] = None
    namespace: Optional[str] = None
    workdir: str = "/workspace"
    env: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_yaml(path: str) -> "JobManifest":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ManifestError("Manifest must be a YAML mapping (dict).")

        required = ["team", "user", "job_type", "gpus", "duration_hours", "image", "priority", "command"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ManifestError(f"Missing required fields: {missing}")

        job_type = str(data["job_type"]).strip()
        if job_type not in VALID_JOB_TYPES:
            raise ManifestError(f"Invalid job_type '{job_type}'. Must be one of {sorted(VALID_JOB_TYPES)}")

        priority = str(data["priority"]).strip()
        if priority not in VALID_PRIORITIES:
            raise ManifestError(f"Invalid priority '{priority}'. Must be one of {sorted(VALID_PRIORITIES)}")

        gpus = int(data["gpus"])
        if gpus <= 0:
            raise ManifestError("gpus must be a positive integer")

        duration_hours = float(data["duration_hours"])
        if duration_hours <= 0:
            raise ManifestError("duration_hours must be > 0")

        env = data.get("env") or {}
        if not isinstance(env, dict):
            raise ManifestError("env must be a mapping (dict)")

        return JobManifest(
            team=str(data["team"]).strip(),
            user=str(data["user"]).strip(),
            job_type=job_type,
            gpus=gpus,
            duration_hours=duration_hours,
            image=str(data["image"]).strip(),
            priority=priority,
            command=str(data["command"]).strip(),
            name=(str(data["name"]).strip() if data.get("name") is not None else None),
            namespace=(str(data["namespace"]).strip() if data.get("namespace") is not None else None),
            workdir=str(data.get("workdir", "/workspace")).strip(),
            env={str(k): str(v) for k, v in env.items()},
        )
