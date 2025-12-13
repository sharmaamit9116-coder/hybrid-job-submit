import datetime as _dt
import json
import shutil
import subprocess
from typing import List, Optional, Tuple


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def run_cmd(args: List[str], timeout_s: int = 60) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    p = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def now_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def pretty_json(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True)
