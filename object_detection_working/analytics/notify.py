"""
Send alerts via Email (SMTP) and/or SMS (Twilio).
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from . import config


def send_email(subject: str, body: str) -> bool:
    if not config.email_configured():
        print("[Analytics] Email not configured (ANALYTICS_SMTP_*, ANALYTICS_ALERT_EMAIL_TO)")
        return False
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = config.ALERT_EMAIL_FROM
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
            if config.SMTP_USER:
                s.starttls()
                s.login(config.SMTP_USER, config.SMTP_PASS)
            to_list = [e.strip() for e in config.ALERT_EMAIL_TO.split(",") if e.strip()]
            s.sendmail(config.ALERT_EMAIL_FROM, to_list, msg.as_string())
        print(f"[Analytics] Email sent: {subject}")
        return True
    except Exception as e:
        print(f"[Analytics] Email failed: {e}")
        return False


def send_sms(body: str) -> bool:
    if not config.sms_configured():
        print("[Analytics] SMS not configured (TWILIO_*, ANALYTICS_ALERT_PHONE_TO)")
        return False
    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        to_list = [p.strip() for p in config.ALERT_PHONE_TO.split(",") if p.strip()]
        for to in to_list:
            client.messages.create(body=body, from_=config.TWILIO_FROM_NUMBER, to=to)
        print(f"[Analytics] SMS sent to {len(to_list)} number(s)")
        return True
    except Exception as e:
        print(f"[Analytics] SMS failed: {e}")
        return False


def send_whatsapp(body: str, media_url: list = None) -> bool:
    """Send via Twilio WhatsApp API. From/To must use whatsapp:+number format.
    media_url: optional list of public URLs to attach (e.g. image of the frame)."""
    if not config.whatsapp_configured():
        print("[Analytics] WhatsApp not configured (TWILIO_*, TWILIO_WHATSAPP_FROM, ANALYTICS_ALERT_WHATSAPP_TO)")
        return False
    try:
        from twilio.rest import Client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        to_list = [p.strip() for p in config.ALERT_WHATSAPP_TO.split(",") if p.strip()]
        kwargs = {"body": body, "from_": config.TWILIO_WHATSAPP_FROM}
        if media_url:
            kwargs["media_url"] = media_url if isinstance(media_url, list) else [media_url]
        for to in to_list:
            if not to.startswith("whatsapp:"):
                to = "whatsapp:" + to
            client.messages.create(to=to, **kwargs)
        print(f"[Analytics] WhatsApp sent to {len(to_list)} number(s)" + (" with media" if media_url else ""))
        return True
    except Exception as e:
        print(f"[Analytics] WhatsApp failed: {e}")
        return False


def send_alert(trigger_name: str, message: str, via_email: bool, via_sms: bool, via_whatsapp: bool = False, body: str = None, media_url: list = None):
    """Send alert. If body is None, use message_template from alert_config with {trigger_name} and {message}."""
    if body is None:
        from . import alert_config
        cfg = alert_config.get_config()
        template = cfg.get("message_template", "{trigger_name}: {message}")
        body = template.replace("{trigger_name}", trigger_name).replace("{message}", message)
    subject = f"[YOLO Alert] {trigger_name}"
    if via_email:
        send_email(subject, body)
    if via_sms:
        send_sms(body)
    if via_whatsapp:
        send_whatsapp(body, media_url=media_url)
