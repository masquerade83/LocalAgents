"""
Analytics and notification config from environment.
Set these in .env or export before running the server.
"""
import os

# SMTP (Email)
SMTP_HOST = os.environ.get("ANALYTICS_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("ANALYTICS_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("ANALYTICS_SMTP_USER", "")
SMTP_PASS = os.environ.get("ANALYTICS_SMTP_PASS", "")
ALERT_EMAIL_FROM = os.environ.get("ANALYTICS_ALERT_EMAIL_FROM", SMTP_USER or "alerts@local")
ALERT_EMAIL_TO = os.environ.get("ANALYTICS_ALERT_EMAIL_TO", "")  # comma-separated

# Twilio (SMS)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
ALERT_PHONE_TO = os.environ.get("ANALYTICS_ALERT_PHONE_TO", "")  # comma-separated, E.164

# Twilio WhatsApp (uses same Twilio account; From = WhatsApp sandbox or Business number)
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")  # e.g. whatsapp:+14155238886 (sandbox)
ALERT_WHATSAPP_TO = os.environ.get("ANALYTICS_ALERT_WHATSAPP_TO", "")  # comma-separated whatsapp:+countrycodeNumber

def email_configured():
    return bool(SMTP_HOST and ALERT_EMAIL_TO)

def sms_configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER and ALERT_PHONE_TO)

def whatsapp_configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM and ALERT_WHATSAPP_TO)
