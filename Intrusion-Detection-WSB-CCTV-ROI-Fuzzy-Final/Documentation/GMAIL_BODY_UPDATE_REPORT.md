# Gmail Alert Body Update Report

## Update Goal

The Gmail alert message was redesigned to look more standard, professional, and suitable for a security monitoring system.

The updated email now includes:

- Professional security alert header
- Clear intrusion date and time
- Severity badge
- Detection source
- Restricted ROI zone information
- ROI status
- Fuzzy class result
- Intrusion confidence
- Risk score
- Fuzzy score
- Alert reason
- Inline screenshot of the intrusion moment
- Screenshot also attached to the email
- Professional footer
- Plain-text fallback body for email clients that do not render HTML well

---

## Main Modified File

```text
services/alert_service.py
```

This file controls the email alert system. It now builds a professional HTML Gmail body before sending the intrusion alert.

---

## Other Files Updated

```text
app.py
services/camera_utils.py
services/video_utils.py
```

These files now pass extra information to the Gmail body:

```text
source
intrusion timestamp
confidence
risk score
ROI status
ROI zone
fuzzy class
fuzzy score
alert reason
```

---

## New Test File Added

```text
test_professional_email_body.py
```

This test checks that the professional email body contains:

- Header
- Footer
- Date
- Time
- Screenshot section
- Inline image content ID
- Correct multipart email structure

---

## Final Email Workflow

```text
Intrusion confirmed
        |
        v
Screenshot saved
        |
        v
Alert details collected
        |
        v
Professional Gmail body created
        |
        v
Screenshot embedded inside email
        |
        v
Screenshot attached to email
        |
        v
Email sent through SMTP
```

---

## Updated Email Subject Example

```text
[CRITICAL] Security Alert: Intrusion Detected in Restricted Area
```

The severity can change depending on the risk score and fuzzy class.

---

## Updated Email Body Structure

```text
Header
    -> Project name
    -> Security alert title
    -> Severity badge

Main body
    -> Intrusion date
    -> Intrusion time
    -> Detection source
    -> Restricted ROI zone
    -> ROI status
    -> Fuzzy class
    -> Confidence
    -> Risk score
    -> Fuzzy score
    -> Alert reason

Screenshot section
    -> Intrusion moment screenshot shown inside the email
    -> Screenshot also attached

Footer
    -> Automated alert notice
    -> Do-not-reply message
    -> Dashboard review instruction
```

---

## Example Email Content

```text
Security Alert: Intrusion Detected

Intrusion Date: 15 July 2026
Intrusion Time: 10:30:45 AM
Detection Source: Live camera
Restricted ROI Zone: Main counter restricted area
ROI Status: Entered restricted ROI
Fuzzy Class: weapon
Intrusion Confidence: 91.0%
Risk Score: 88.0/100
Fuzzy Score: 92.0/100

Recommended action: Review the screenshot, verify the location, and take the necessary security response.
```

---

## Test Result

```text
40 passed
2 skipped
0 failed
```

The skipped tests are live-email tests only. No real email was sent during normal testing.

---

## Important Note

For the first local run, keep email mode disabled/manual:

```env
EMAIL_TRIGGER_MODE=MANUAL
```

After image, video, live camera, ROI, and fuzzy logic work properly, use fresh Gmail app-password credentials and change the mode when you want real email alerts.
