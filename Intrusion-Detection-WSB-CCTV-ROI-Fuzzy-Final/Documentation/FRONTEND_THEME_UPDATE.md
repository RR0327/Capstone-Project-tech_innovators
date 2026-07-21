# Frontend Theme Update

## What was changed

The frontend was updated with a security-dashboard style suitable for the Hybrid Intrusion Detection, ROI, and Fuzzy Logic project.

## Main design idea

The new design uses:

- Dark CCTV/security background
- Navy and deep-blue dashboard style
- Red alert color for intrusion
- Green color for safe/non-intrusion status
- Yellow/amber accent for restricted ROI area
- Cleaner cards, buttons, panels, result metrics, and live camera dashboard

## Files modified

```text
static/css/style.css
templates/index.html
templates/result.html
templates/live_camera.html
```

## Why a shared CSS file was added

Previously each template had its own CSS inside the HTML file. Now the main styling is stored in:

```text
static/css/style.css
```

This makes the frontend easier to maintain. If you want to change the website color later, you can mainly edit this one file.

## Important colors

Open this file:

```text
static/css/style.css
```

Then change these variables:

```css
:root {
  --bg-1: #07111f;
  --bg-2: #0b1f35;
  --primary: #1b8cff;
  --roi: #ffc400;
  --danger: #e53935;
  --success: #13a66b;
}
```

Meaning:

```text
--bg-1 / --bg-2 -> website background
--primary       -> main button and blue accent
--roi           -> ROI/restricted-area accent
--danger        -> intrusion alert color
--success       -> no-alert/safe color
```

## Backend impact

No backend detection logic was changed. The intrusion model, ROI checking, fuzzy logic, alert decision, email system, and tests remain the same.

## Final frontend workflow shown to the user

```text
Input image/video/live camera
        |
        v
Intrusion model checks detection
        |
        v
Detected bounding box enters restricted ROI?
        |
        v
Fuzzy logic checks class/person type
        |
        v
Final alert decision shown on dashboard
```
