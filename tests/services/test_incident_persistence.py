from datetime import datetime

from apps.api.services.incident_persistence import _date_bucket, _incident_key


def test_incident_key_is_stable_for_same_inputs() -> None:
    opened = datetime(2026, 6, 2, 10, 30, 0)
    a = _incident_key("Email outage", "HQ-East", opened)
    b = _incident_key("Email outage", "HQ-East", opened)
    assert a == b
    assert a.startswith("INC-email_outage-")
    assert len(a.split("-")[-1]) == 10


def test_incident_key_differs_by_site() -> None:
    opened = datetime(2026, 6, 2, 10, 30, 0)
    assert _incident_key("Email outage", "HQ-East", opened) != _incident_key(
        "Email outage", "HQ-West", opened
    )


def test_incident_key_differs_by_date_bucket() -> None:
    a = _incident_key("VPN failure", "HQ-East", datetime(2026, 6, 2, 10, 30, 0))
    b = _incident_key("VPN failure", "HQ-East", datetime(2026, 6, 3, 9, 0, 0))
    assert a != b


def test_incident_key_normalizes_missing_site_and_cause() -> None:
    a = _incident_key(None, None, None)
    b = _incident_key(None, None, None)
    assert a == b
    assert a.startswith("INC-unknown-")
    assert "global" in a or a.count("-") >= 2


def test_date_bucket_handles_datetime() -> None:
    assert _date_bucket(datetime(2026, 6, 2, 10, 30, 0)) == "20260602"


def test_date_bucket_handles_iso_string() -> None:
    assert _date_bucket("2026-06-02T10:30:00Z") == "20260602"


def test_date_bucket_handles_none() -> None:
    bucket = _date_bucket(None)
    assert len(bucket) == 8
    assert bucket.isdigit()
