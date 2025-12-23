from dataclasses import dataclass
from typing import Dict

from .errors import QuotaExceededError


@dataclass(frozen=True)
class TeamQuota:
    max_gpus: int


# Hard-coded Quota.
TEAM_QUOTAS: Dict[str, TeamQuota] = {
    "vision-china": TeamQuota(max_gpus=128),
    "nlp-us": TeamQuota(max_gpus=256),
    "recsys-eu": TeamQuota(max_gpus=64),
    "default": TeamQuota(max_gpus=32),
}


def get_team_quota(team: str) -> TeamQuota:
    return TEAM_QUOTAS.get(team, TEAM_QUOTAS["default"])


def enforce_quota(team: str, requested_gpus: int) -> None:
    quota = get_team_quota(team)
    if requested_gpus > quota.max_gpus:
        raise QuotaExceededError(
            f"Quota exceeded for team '{team}': requested {requested_gpus} GPUs, "
            f"limit is {quota.max_gpus} GPUs."
        )
