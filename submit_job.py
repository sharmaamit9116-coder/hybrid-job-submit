#!/usr/bin/env python
import argparse
import sys

from hybrid_job_submit.errors import HybridSubmitError
from hybrid_job_submit.manifest import JobManifest
from hybrid_job_submit.router import route_and_submit
from hybrid_job_submit.utils import pretty_json


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid Slurm/Kubernetes job submitter")
    ap.add_argument("--config", required=True, help="Path to job manifest YAML")
    ap.add_argument("--dry-run", action="store_true", help="Do not submit; print what would be submitted")
    args = ap.parse_args()

    try:
        manifest = JobManifest.from_yaml(args.config)
        result = route_and_submit(manifest, dry_run=args.dry_run)
        print(pretty_json(result))
        return 0
    except HybridSubmitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
