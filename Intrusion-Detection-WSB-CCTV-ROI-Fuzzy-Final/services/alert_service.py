"""Email alert service for intrusion events."""

from __future__ import annotations

import html
import os
import smtplib
import time
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import cv2


class AlertService:
    MODES = {
        "ALWAYS": 0,
        "COOLDOWN_60": 60,
        "COOLDOWN_300": 300,
        "COOLDOWN_3600": 3600,
        "MANUAL": float("inf"),
    }

    def __init__(self) -> None:
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.alert_email = os.getenv("ALERT_EMAIL", "")
        self.project_name = os.getenv(
            "EMAIL_PROJECT_NAME",
            "Hybrid CCTV Intrusion Detection System",
        )
        self.email_trigger_mode = os.getenv(
            "EMAIL_TRIGGER_MODE", "COOLDOWN_60"
        ).upper()
        if self.email_trigger_mode not in self.MODES:
            self.email_trigger_mode = "COOLDOWN_60"
        self.cooldown_duration = self.MODES[self.email_trigger_mode]
        self.last_email_sent_time = 0.0
        self.alert_dir = os.getenv("ALERT_DIR", "static/alerts")
        os.makedirs(self.alert_dir, exist_ok=True)

    def configured(self) -> bool:
        return bool(self.sender_email and self.sender_password and self.alert_email)

    def save_screenshot(self, frame, prefix: str = "intrusion") -> str | None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(self.alert_dir, f"{prefix}_{timestamp}.jpg")
        return path if cv2.imwrite(path, frame) else None

    def should_send_email(self) -> tuple[bool, str]:
        if self.email_trigger_mode == "MANUAL":
            return False, "Automatic email is disabled."
        elapsed = time.time() - self.last_email_sent_time
        if elapsed >= self.cooldown_duration:
            return True, "Email trigger is ready."
        return False, f"Cooldown active for {self.cooldown_duration - elapsed:.0f} seconds."

    def get_trigger_status(self) -> dict[str, Any]:
        can_send, reason = self.should_send_email()
        elapsed = time.time() - self.last_email_sent_time
        remaining = (
            0
            if self.cooldown_duration == float("inf")
            else max(0.0, self.cooldown_duration - elapsed)
        )
        return {
            "trigger_mode": self.email_trigger_mode,
            "cooldown_seconds": self.cooldown_duration,
            "time_since_last_email": elapsed,
            "remaining_cooldown": remaining,
            "can_send_now": can_send,
            "reason": reason,
            "configured": self.configured(),
        }

    def set_trigger_mode(self, mode: str) -> dict[str, Any]:
        mode = str(mode).upper()
        if mode not in self.MODES:
            return {"success": False, "error": f"Unsupported mode: {mode}"}
        self.email_trigger_mode = mode
        self.cooldown_duration = self.MODES[mode]
        return {
            "success": True,
            "new_mode": mode,
            "cooldown_seconds": self.cooldown_duration,
            "note": "This change lasts until the application restarts.",
        }

    @staticmethod
    def _format_percent(value: Any) -> str:
        try:
            numeric = float(value or 0.0)
        except (TypeError, ValueError):
            numeric = 0.0
        return f"{numeric:.1%}"

    @staticmethod
    def _format_score(value: Any, suffix: str = "/100") -> str:
        try:
            numeric = float(value or 0.0)
        except (TypeError, ValueError):
            numeric = 0.0
        return f"{numeric:.1f}{suffix}"

    @staticmethod
    def _parse_event_datetime(details: dict[str, Any]) -> datetime:
        """Return the event time used in the email body.

        Supported detail keys: timestamp, event_time, intrusion_time, detected_at.
        If the caller does not provide a time, the server's current time is used.
        """
        raw_value = (
            details.get("timestamp")
            or details.get("event_time")
            or details.get("intrusion_time")
            or details.get("detected_at")
        )
        if isinstance(raw_value, datetime):
            return raw_value
        if raw_value:
            text = str(raw_value).strip()
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S",
            ):
                try:
                    return datetime.strptime(text[:19], fmt)
                except ValueError:
                    continue
        return datetime.now()

    @staticmethod
    def _safe_text(value: Any, default: str = "N/A") -> str:
        if value is None or value == "":
            return default
        return html.escape(str(value))

    @staticmethod
    def _risk_badge(risk_score: float, fuzzy_class: str) -> tuple[str, str, str]:
        """Return severity label, header color, and badge background color."""
        normalized_class = str(fuzzy_class or "").lower()
        if normalized_class == "weapon" or risk_score >= 85:
            return "CRITICAL", "#7f1d1d", "#dc2626"
        if risk_score >= 70:
            return "HIGH", "#991b1b", "#ef4444"
        if risk_score >= 45:
            return "MEDIUM", "#92400e", "#f59e0b"
        return "LOW", "#1e3a8a", "#3b82f6"

    def _build_plain_text_body(
        self,
        details: dict[str, Any],
        event_time: datetime,
        severity: str,
        has_image: bool,
    ) -> str:
        confidence = self._format_percent(details.get("confidence", 0.0))
        risk_score = self._format_score(details.get("risk_score", 0.0))
        fuzzy_score = self._format_score(details.get("fuzzy_score", 0.0))
        return f"""{self.project_name}
Security Alert: Intrusion Detected

Severity: {severity}
Date: {event_time.strftime('%d %B %Y')}
Time: {event_time.strftime('%I:%M:%S %p')}
Source: {details.get('source') or details.get('detection_source') or 'Security camera / uploaded media'}
Restricted ROI Zone: {details.get('roi_zone') or details.get('roi_zone_name') or 'Restricted area'}
ROI Status: {details.get('roi_status') or 'Entered restricted ROI'}
Fuzzy Class: {details.get('fuzzy_class') or details.get('roi_context') or 'N/A'}
Confidence: {confidence}
Risk Score: {risk_score}
Fuzzy Score: {fuzzy_score}
Reason: {details.get('reason') or 'Intrusion detected.'}

Screenshot: {'Attached and embedded in the HTML email body.' if has_image else 'No screenshot was attached.'}

This is an automated alert generated by {self.project_name}. Please review the evidence and take appropriate action.
"""

    def _build_html_body(
        self,
        details: dict[str, Any],
        event_time: datetime,
        image_path: str | None,
    ) -> str:
        confidence = self._format_percent(details.get("confidence", 0.0))
        risk_score_value = float(details.get("risk_score", 0.0) or 0.0)
        risk_score = self._format_score(risk_score_value)
        fuzzy_score = self._format_score(details.get("fuzzy_score", 0.0))
        fuzzy_class = str(details.get("fuzzy_class") or details.get("roi_context") or "N/A")
        severity, header_color, badge_color = self._risk_badge(risk_score_value, fuzzy_class)
        reason = self._safe_text(details.get("reason"), "Intrusion detected.")
        source = self._safe_text(
            details.get("source") or details.get("detection_source"),
            "Security camera / uploaded media",
        )
        roi_zone = self._safe_text(
            details.get("roi_zone") or details.get("roi_zone_name"),
            "Restricted area",
        )
        roi_status = self._safe_text(details.get("roi_status"), "Entered restricted ROI")
        track_id = self._safe_text(details.get("track_id"), "N/A")
        screenshot_block = """
              <div style="margin-top:22px">
                <h3 style="margin:0 0 10px 0;color:#111827;font-size:16px">Intrusion Moment Screenshot</h3>
                <p style="margin:0 0 10px 0;color:#6b7280;font-size:13px">
                  The image below shows the frame captured at the moment of the confirmed alert.
                </p>
                <img src="cid:intrusion_frame" alt="Intrusion moment screenshot"
                     style="display:block;width:100%;max-width:760px;border:1px solid #d1d5db;border-radius:12px;margin:0 auto;background:#111827" />
              </div>
        """ if image_path else """
              <div style="margin-top:22px;padding:14px;border:1px dashed #d1d5db;border-radius:10px;color:#6b7280;background:#f9fafb">
                No screenshot was attached for this alert.
              </div>
        """

        return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#eef2f7;font-family:Arial,Helvetica,sans-serif;color:#111827">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f7;padding:24px 0">
      <tr>
        <td align="center">
          <table role="presentation" width="760" cellpadding="0" cellspacing="0" style="width:760px;max-width:94%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(15,23,42,0.14)">
            <tr>
              <td style="background:{header_color};padding:24px 28px;color:#ffffff">
                <div style="font-size:13px;letter-spacing:1.6px;text-transform:uppercase;opacity:0.92">{html.escape(self.project_name)}</div>
                <h1 style="margin:8px 0 0 0;font-size:26px;line-height:1.25">Security Alert: Intrusion Detected</h1>
                <div style="margin-top:14px;display:inline-block;background:{badge_color};color:#ffffff;padding:7px 14px;border-radius:999px;font-weight:bold;font-size:13px;letter-spacing:0.6px">
                  Severity: {severity}
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:26px 28px">
                <p style="margin:0 0 18px 0;font-size:15px;line-height:1.65;color:#374151">
                  The monitoring system detected an intrusion event in the restricted ROI workflow.
                  Please review the event details and the attached screenshot evidence.
                </p>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">
                  <tr>
                    <td style="width:34%;padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Intrusion Date</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{event_time.strftime('%d %B %Y')}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Intrusion Time</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{event_time.strftime('%I:%M:%S %p')}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Detection Source</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{source}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Restricted ROI Zone</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{roi_zone}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">ROI Status</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{roi_status}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Fuzzy Class</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{html.escape(fuzzy_class)}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Intrusion Confidence</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{confidence}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Risk Score</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{risk_score}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Fuzzy Score</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{fuzzy_score}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;border-bottom:1px solid #e5e7eb;font-weight:bold;color:#374151">Track ID</td>
                    <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#111827">{track_id}</td>
                  </tr>
                  <tr>
                    <td style="padding:12px 14px;background:#f9fafb;font-weight:bold;color:#374151">Alert Reason</td>
                    <td style="padding:12px 14px;color:#111827;line-height:1.55">{reason}</td>
                  </tr>
                </table>

                {screenshot_block}

                <div style="margin-top:22px;padding:16px 18px;background:#fff7ed;border-left:4px solid #f97316;border-radius:10px;color:#7c2d12;line-height:1.55">
                  <b>Recommended action:</b> Review the screenshot, verify the location, and take the necessary security response.
                </div>
              </td>
            </tr>
            <tr>
              <td style="background:#111827;color:#d1d5db;padding:18px 28px;text-align:center;font-size:12px;line-height:1.6">
                This is an automated notification generated by {html.escape(self.project_name)}.<br />
                Please do not reply to this email. Check the monitoring dashboard for full evidence and logs.<br />
                Generated at {datetime.now().strftime('%d %B %Y, %I:%M:%S %p')} server time.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
        """

    def send_intrusion_alert(
        self,
        image_path: str | None,
        detection_details: dict[str, Any] | None = None,
        force: bool = False,
    ) -> bool:
        if not self.configured():
            print("Email alert skipped: SMTP credentials are not configured.")
            return False
        if not force:
            allowed, reason = self.should_send_email()
            if not allowed:
                print(f"Email alert skipped: {reason}")
                return False

        details = detection_details or {}
        event_time = self._parse_event_datetime(details)
        fuzzy_class = str(details.get("fuzzy_class") or details.get("roi_context") or "")
        risk_score = float(details.get("risk_score", 0.0) or 0.0)
        severity, _, _ = self._risk_badge(risk_score, fuzzy_class)
        has_image = bool(image_path and os.path.exists(image_path))

        message = MIMEMultipart("related")
        message["From"] = self.sender_email
        message["To"] = self.alert_email
        message["Subject"] = f"[{severity}] Security Alert: Intrusion Detected in Restricted Area"

        alternative = MIMEMultipart("alternative")
        alternative.attach(
            MIMEText(
                self._build_plain_text_body(details, event_time, severity, has_image),
                "plain",
                "utf-8",
            )
        )
        alternative.attach(
            MIMEText(
                self._build_html_body(details, event_time, image_path if has_image else None),
                "html",
                "utf-8",
            )
        )
        message.attach(alternative)

        if has_image:
            with open(image_path, "rb") as image_file:
                image = MIMEImage(image_file.read())
            image.add_header("Content-ID", "<intrusion_frame>")
            image.add_header("Content-Disposition", "inline", filename=os.path.basename(image_path))
            message.attach(image)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            self.last_email_sent_time = time.time()
            return True
        except Exception as exc:
            print(f"Email alert failed: {exc}")
            return False

    # Backward-compatible name used by older application code.
    def send_email_alert(
        self,
        image_path: str,
        fire_type: str = "intrusion",
        detection_details: dict[str, Any] | None = None,
        force: bool = False,
    ) -> bool:
        return self.send_intrusion_alert(image_path, detection_details, force)
