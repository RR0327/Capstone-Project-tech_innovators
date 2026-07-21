from __future__ import annotations

import base64
from email import message_from_bytes

from services.alert_service import AlertService


class FakeSMTP:
    sent_messages = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        return None

    def login(self, user, password):
        self.user = user
        self.password = password

    def send_message(self, message):
        self.sent_messages.append(message)


def test_professional_gmail_body_contains_header_footer_time_and_screenshot(monkeypatch, tmp_path):
    FakeSMTP.sent_messages.clear()
    monkeypatch.setenv("SENDER_EMAIL", "sender@example.com")
    monkeypatch.setenv("SENDER_PASSWORD", "app-password")
    monkeypatch.setenv("ALERT_EMAIL", "receiver@example.com")
    monkeypatch.setenv("EMAIL_TRIGGER_MODE", "ALWAYS")
    monkeypatch.setattr("services.alert_service.smtplib.SMTP", FakeSMTP)

    # 1x1 PNG file so MIMEImage can identify the screenshot type.
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    image_path = tmp_path / "intrusion_moment.png"
    image_path.write_bytes(png_bytes)

    service = AlertService()
    sent = service.send_intrusion_alert(
        str(image_path),
        {
            "source": "Live camera",
            "timestamp": "2026-07-15 10:30:45",
            "confidence": 0.91,
            "risk_score": 88,
            "fuzzy_score": 92,
            "fuzzy_class": "weapon",
            "roi_status": "Entered restricted ROI",
            "roi_zone": "Main counter restricted area",
            "reason": "Weapon detected inside restricted ROI after intrusion detection.",
        },
        force=True,
    )

    assert sent is True
    assert len(FakeSMTP.sent_messages) == 1
    message = FakeSMTP.sent_messages[0]
    assert "Security Alert: Intrusion Detected" in message["Subject"]

    raw = message.as_bytes()
    parsed = message_from_bytes(raw)
    body_parts = []
    for part in parsed.walk():
        if part.get_content_type() in {"text/plain", "text/html"}:
            body_parts.append(part.get_payload(decode=True).decode("utf-8", errors="ignore"))
    payload_text = "\n".join(body_parts)

    assert "Hybrid CCTV Intrusion Detection System" in payload_text
    assert "Security Alert: Intrusion Detected" in payload_text
    assert "Intrusion Date" in payload_text
    assert "15 July 2026" in payload_text
    assert "10:30:45 AM" in payload_text
    assert "Intrusion Moment Screenshot" in payload_text
    assert "Please do not reply to this email" in payload_text
    assert "Content-ID: <intrusion_frame>" in raw.decode("utf-8", errors="ignore")
    assert parsed.is_multipart()
