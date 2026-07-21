"""Safe email setup check. It never sends an email."""


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

from services.alert_service import AlertService


def main():
    service = AlertService()
    print(f"SMTP configured: {service.configured()}")
    print(f"Trigger mode: {service.email_trigger_mode}")
    print("No email was sent.")


if __name__ == "__main__":
    main()
