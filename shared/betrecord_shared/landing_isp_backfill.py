"""One-time backfill of isp / isp_country on historic landing_hits rows."""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import or_, select, update

from .database import SessionLocal
from .ip_lookup import lookup_ip
from .models import LandingHit

# ip-api.com free tier: 45 requests/minute per source IP.
_LOOKUP_INTERVAL_SEC = 1.4


@dataclass(frozen=True)
class LandingIspBackfillResult:
    unique_ips: int
    looked_up: int
    resolved: int
    failed: int
    updated_rows: int


def backfill_landing_isp(*, dry_run: bool = False) -> LandingIspBackfillResult:
    """Fill isp and isp_country for landing hits recorded before those columns existed."""
    with SessionLocal() as db:
        ips = list(
            db.scalars(
                select(LandingHit.ip_address)
                .where(
                    LandingHit.ip_address.isnot(None),
                    or_(LandingHit.isp.is_(None), LandingHit.isp_country.is_(None)),
                )
                .distinct()
            ).all()
        )

        looked_up = 0
        resolved = 0
        failed = 0
        updated_rows = 0

        for ip in ips:
            if not ip:
                continue
            looked_up += 1
            info = lookup_ip(ip)
            if info is None:
                failed += 1
                time.sleep(_LOOKUP_INTERVAL_SEC)
                continue

            resolved += 1
            if dry_run:
                row_ids = db.scalars(
                    select(LandingHit.id).where(
                        LandingHit.ip_address == ip,
                        or_(LandingHit.isp.is_(None), LandingHit.isp_country.is_(None)),
                    )
                ).all()
                updated_rows += len(row_ids)
            else:
                result = db.execute(
                    update(LandingHit)
                    .where(
                        LandingHit.ip_address == ip,
                        or_(LandingHit.isp.is_(None), LandingHit.isp_country.is_(None)),
                    )
                    .values(isp=info.isp, isp_country=info.country)
                )
                updated_rows += result.rowcount or 0

            time.sleep(_LOOKUP_INTERVAL_SEC)

        if not dry_run:
            db.commit()

        return LandingIspBackfillResult(
            unique_ips=len(ips),
            looked_up=looked_up,
            resolved=resolved,
            failed=failed,
            updated_rows=updated_rows,
        )
