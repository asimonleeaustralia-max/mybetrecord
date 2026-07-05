"""Tests for landing ISP backfill."""

from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from betrecord_shared.database import SessionLocal, init_db
from betrecord_shared.ip_lookup import IpLookupResult, lookup_ip
from betrecord_shared.landing_isp_backfill import backfill_landing_isp
from betrecord_shared.models import LandingHit


@pytest.fixture
def db():
    init_db()
    with SessionLocal() as session:
        session.execute(delete(LandingHit))
        session.commit()
        yield session
        session.execute(delete(LandingHit))
        session.commit()


def test_backfill_landing_isp(db):
    db.add_all(
        [
            LandingHit(path="/", ip_address="8.8.8.8", browser="Chrome"),
            LandingHit(path="/", ip_address="8.8.8.8", browser="Firefox"),
            LandingHit(path="/", ip_address="1.1.1.1", browser="Safari"),
            LandingHit(
                path="/",
                ip_address="9.9.9.9",
                browser="Edge",
                isp="Existing ISP",
                isp_country="AU",
            ),
        ]
    )
    db.commit()

    lookup_ip.cache_clear()
    with patch(
        "betrecord_shared.landing_isp_backfill.lookup_ip",
        side_effect=lambda ip: {
            "8.8.8.8": IpLookupResult(isp="Google LLC", country="US"),
            "1.1.1.1": IpLookupResult(isp="Cloudflare", country="US"),
        }.get(ip),
    ), patch("betrecord_shared.landing_isp_backfill.time.sleep"):
        result = backfill_landing_isp()

    assert result.unique_ips == 2
    assert result.resolved == 2
    assert result.updated_rows == 3

    rows = {row.browser: row for row in db.scalars(select(LandingHit)).all()}
    assert rows["Chrome"].isp == "Google LLC"
    assert rows["Firefox"].isp == "Google LLC"
    assert rows["Safari"].isp == "Cloudflare"
    assert rows["Edge"].isp == "Existing ISP"


def test_backfill_landing_isp_dry_run(db):
    db.add(LandingHit(path="/", ip_address="8.8.8.8"))
    db.commit()

    lookup_ip.cache_clear()
    with patch(
        "betrecord_shared.landing_isp_backfill.lookup_ip",
        return_value=IpLookupResult(isp="Google LLC", country="US"),
    ), patch("betrecord_shared.landing_isp_backfill.time.sleep"):
        result = backfill_landing_isp(dry_run=True)

    assert result.updated_rows == 1
    db.expire_all()
    row = db.scalar(select(LandingHit))
    assert row.isp is None
    assert row.isp_country is None
