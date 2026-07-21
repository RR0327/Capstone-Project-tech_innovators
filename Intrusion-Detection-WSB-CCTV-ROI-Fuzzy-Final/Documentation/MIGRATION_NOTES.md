# Fire/Smoke to Intrusion Migration

The old fire/smoke wording and logic were removed from the active system.

Key changes:

- `FireDetector` was replaced by `IntrusionDetector`; a temporary alias remains for old imports.
- Good-fire, bad-fire, smoke, fuzzy-fire, and fire-risk rules were removed.
- The local model path is now `Models/best.pt`.
- The model is treated as one-class intrusion detection.
- OBB extraction is used for `result.obb`.
- Image, video, live camera, result pages, email text, tests, README, and defence report now use intrusion terminology.
- Hardcoded email, Twilio, and Roboflow secrets were removed.
- Old fire test files were replaced with intrusion-specific tests.
