from services.alert_service import AlertService


def test_email_mode_can_be_changed_without_sending(monkeypatch):
    monkeypatch.delenv("SENDER_EMAIL", raising=False)
    service = AlertService()
    result = service.set_trigger_mode("COOLDOWN_300")
    assert result["success"] is True
    assert service.cooldown_duration == 300


def test_invalid_mode_is_rejected():
    result = AlertService().set_trigger_mode("UNKNOWN")
    assert result["success"] is False
