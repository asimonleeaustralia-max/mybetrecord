#!/usr/bin/env python3
"""Backfill isp / isp_country on historic landing_hits rows.

Usage (from repo root, with DATABASE_URL set):
  python scripts/backfill_landing_isp.py
  python scripts/backfill_landing_isp.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared"))

from betrecord_shared.landing_isp_backfill import backfill_landing_isp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many rows would be updated without writing",
    )
    args = parser.parse_args()

    result = backfill_landing_isp(dry_run=args.dry_run)
    mode = "would update" if args.dry_run else "updated"
    print(
        f"unique_ips={result.unique_ips} looked_up={result.looked_up} "
        f"resolved={result.resolved} failed={result.failed} {mode}={result.updated_rows}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
