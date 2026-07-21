from services.alert_service import AlertService


def test_missing_credentials_are_reported(monkeypatch):
    for name in ("SENDER_EMAIL", "SENDER_PASSWORD", "ALERT_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    assert AlertService().configured() is False
