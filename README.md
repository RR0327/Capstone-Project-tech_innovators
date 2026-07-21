# Hybrid Intrusion Detection with ROI and Fuzzy Logic

A Flask-based CCTV monitoring project for images, uploaded videos, and a server-side live camera. The active decision flow is:

```text
YOLOv8 OBB intrusion detection
    -> restricted ROI validation
    -> ROI/person-context classification
    -> fuzzy scoring
    -> final alert decision
    -> evidence saving and optional Gmail alert
```

## Important model interpretation

The primary model has one class: `intrusion`. `non_intrusion` is an application result meaning that no candidate satisfied the current detection and decision rules; it is not a separately trained class.

## Required model files

Copy the original checkpoints into `Models/`:

```text
Models/best.pt
Models/last.pt
Models/roi_best.pt
Models/roi_last.pt
```

`best.pt` is required to start the application. `roi_best.pt` supplies optional person-context detection. Manual ROI zones now work even when the secondary model is absent.

## Setup on Windows PowerShell

```powershell
cd Intrusion-Detection-WSB-CCTV-ROI-Fuzzy-Final
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python final_verification.py
pytest -q
python app.py
```

Open `http://127.0.0.1:5000`.

## Setup on Linux/macOS

```bash
cd Intrusion-Detection-WSB-CCTV-ROI-Fuzzy-Final
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python final_verification.py
pytest -q
python app.py
```

## Configure the restricted area

Edit `.env` and define one or more normalized boxes:

```env
ROI_MANUAL_ZONES=[{"name":"cash_counter","bbox":[0.45,0.20,0.95,0.95]}]
REQUIRE_ROI_FOR_ALERT=true
```

Coordinates use `[x1, y1, x2, y2]`, with values from `0` to `1`.

## Email safety

Automatic email is disabled in the supplied template:

```env
EMAIL_TRIGGER_MODE=MANUAL
```

Add a fresh Gmail app password only to your private `.env`. Never commit `.env`. To run the protected real-email test:

```powershell
$env:ALLOW_LIVE_EMAIL_TEST="1"
pytest -q tests/test_email.py
```

## Tests

```bash
pytest -q
```

Model-checkpoint tests skip when the binary `.pt` files are absent and run automatically after the files are added.

## Manual tools

Run tools from the project root:

```bash
python tools/debug_yolo.py --model Models/best.pt
python tools/verify_fix.py path/to/image.jpg
python tools/test_threshold_comparison.py path/to/image.jpg --low 0.20 --high 0.40
python tools/email_trigger_control.py
python tools/test_email_setup.py
```

## Main routes

- `/` — dashboard
- `/detect-image` — image upload
- `/detect-video` — video upload
- `/live-camera` — live monitoring page
- `/start-camera`, `/stop-camera`, `/video-feed`, `/get-detections` — live camera APIs
- `/api/model-info` — loaded model information
- `/api/email-trigger-status`, `/api/email-trigger-modes`, `/api/email-trigger-set` — alert-mode APIs

## Known deployment checks

Before claiming deployment readiness, test the actual webcam, real SMTP credentials, and a labelled local CCTV test set. Validation CSV metrics do not guarantee performance in a new location.
