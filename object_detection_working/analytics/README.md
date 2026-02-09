# Analytics layer

- **Dashboard:** http://localhost:5001/dashboard  
- **Storage:** SQLite `analytics/analytics.db` (detection events, triggers, alerts sent).
- **Capture:** Start from the dashboard with an RTSP URL; runs YOLO at a configurable interval and stores detections.

## Reports

- Set **From / To** (date-time) and **Load report** to see:
  - Bar chart: counts by **class**, by **hour**, or by **day**.
  - Table: recent detection events in that range.

## Triggers and alerts

- **class_detected:** Fires when a given class is detected (optional min confidence).
- **count_above:** Fires when the count of a class in the current frame is ≥ threshold (use with cooldown to avoid spam).
- **Cooldown:** Minimum seconds between alerts per trigger.
- **Channels:** Email, SMS, and/or WhatsApp (configured via env). Enable per trigger in the dashboard.

### Email (SMTP)

Set in environment:

| Variable | Example | Description |
|----------|---------|-------------|
| `ANALYTICS_SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `ANALYTICS_SMTP_PORT` | `587` | TLS port |
| `ANALYTICS_SMTP_USER` | `you@gmail.com` | Login |
| `ANALYTICS_SMTP_PASS` | (app password) | Use app password for Gmail |
| `ANALYTICS_ALERT_EMAIL_FROM` | (optional) | Sender address; defaults to SMTP_USER |
| `ANALYTICS_ALERT_EMAIL_TO` | `a@x.com,b@y.com` | Comma-separated recipients |

**Gmail:** Use an [App Password](https://support.google.com/accounts/answer/185833), not your normal password.

### SMS (Twilio)

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | From Twilio console |
| `TWILIO_AUTH_TOKEN` | From Twilio console |
| `TWILIO_FROM_NUMBER` | Your Twilio number (E.164, e.g. `+1234567890`) |
| `ANALYTICS_ALERT_PHONE_TO` | Comma-separated E.164 numbers |

Install: `pip install twilio`

### WhatsApp (Twilio WhatsApp API)

Uses the **same Twilio account** as SMS. From/To must use the `whatsapp:+number` format.

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Same as SMS |
| `TWILIO_WHATSAPP_FROM` | Sender: `whatsapp:+14155238886` (sandbox) or your Twilio WhatsApp Business number |
| `ANALYTICS_ALERT_WHATSAPP_TO` | Recipients: `whatsapp:+919876543210` or comma-separated list |

**Twilio WhatsApp sandbox (testing):**
1. Open [Twilio Console → Try it out → Send a WhatsApp message](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn).
2. Join the sandbox by sending the code from your WhatsApp to the number shown.
3. Set `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886` (or the number shown).
4. Set `ANALYTICS_ALERT_WHATSAPP_TO=whatsapp:+91XXXXXXXXXX` (your number with country code).

**Production:** Use a [Twilio WhatsApp Business](https://www.twilio.com/whatsapp) approved sender.

Install: `pip install twilio` (same as SMS).

---

See `analytics/env.example` for a full template.
