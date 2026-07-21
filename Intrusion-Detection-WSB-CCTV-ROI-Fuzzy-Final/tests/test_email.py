"""Optional live SMTP test. Disabled unless ALLOW_LIVE_EMAIL_TEST=1."""

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from services.alert_service import AlertService


def test_live_email_only_when_explicitly_enabled():
    if os.getenv("ALLOW_LIVE_EMAIL_TEST") != "1":
        pytest.skip("Set ALLOW_LIVE_EMAIL_TEST=1 to send a real test email.")
    service = AlertService()
    assert service.configured(), "Fill SMTP values in .env first."
    assert service.send_intrusion_alert(
        None,
        {"confidence": 0.99, "risk_score": 99, "reason": "Explicit SMTP test"},
        force=True,
    )
