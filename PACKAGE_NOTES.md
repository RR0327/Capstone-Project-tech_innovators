# Package notes

This package was assembled from the source, frontend, training-evidence, test, tool, and documentation files supplied in the conversation.

## Not included

The original binary model checkpoints were referenced but were not available as local uploaded files during packaging:

- `Models/best.pt`
- `Models/last.pt`
- `Models/roi_best.pt`
- `Models/roi_last.pt`

Copy those original files into `Models/`. The package intentionally contains no fabricated checkpoint files and no private `.env` credentials.

## Included integration correction

Manual ROI zones now run independently of the optional secondary ROI model in image, video, and live-camera processing. A regression test was added for this behavior.
