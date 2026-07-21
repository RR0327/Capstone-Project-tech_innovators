"""Show available email trigger modes without exposing credentials."""


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from services.alert_service import AlertService


def main() -> None:
    service = AlertService()
    status = service.get_trigger_status()
    print("Email trigger status")
    print("=" * 40)
    print(f"Configured: {status['configured']}")
    print(f"Mode: {status['trigger_mode']}")
    print(f"Can send now: {status['can_send_now']}")
    print(f"Reason: {status['reason']}")
    print("\nAvailable modes: ALWAYS, COOLDOWN_60, COOLDOWN_300, COOLDOWN_3600, MANUAL")
    print("Set EMAIL_TRIGGER_MODE in .env, then restart the app.")


if __name__ == "__main__":
    main()
