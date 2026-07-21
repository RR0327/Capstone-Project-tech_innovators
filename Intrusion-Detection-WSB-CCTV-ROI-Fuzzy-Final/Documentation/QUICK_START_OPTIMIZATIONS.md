# Quick Start

1. Copy `.env.example` to `.env`.
2. Keep `MODEL_PATH=Models/best.pt`.
3. Install packages with `pip install -r requirements.txt`.
4. Run `python app.py`.
5. Test one clear intrusion image, one normal image, and one short video.
6. Review confidence and risk before changing thresholds.

For live monitoring, start with `CAMERA_FRAME_SKIP=2` and `LIVE_CONF_THRESHOLD=0.30`.
