"""
SMS / WhatsApp Notification Service
====================================
Supports:
  - MSG91  (India - recommended, cheap, DLT compliant)
  - Twilio (international fallback)
  - WhatsApp via Meta Cloud API

Configuration in LabSettings:
  sms_provider      : 'msg91' | 'twilio' | 'none'
  msg91_auth_key    : MSG91 auth key
  msg91_sender_id   : 6-char DLT registered sender ID
  msg91_template_id : DLT registered template ID
  twilio_account_sid, twilio_auth_token, twilio_from_number
  whatsapp_enabled  : bool
  whatsapp_token    : Meta API access token
  whatsapp_phone_id : Meta phone number ID

Usage:
  from lab.notifications import send_report_ready_sms, send_whatsapp_report
  send_report_ready_sms(report)
"""
import json
import logging
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_settings():
    from .models import LabSettings
    return LabSettings.get()


# --- MSG91 --------------------------------------------------------------------

def send_sms_msg91(mobile: str, message: str, template_id: str = None, auth_key: str = None, sender_id: str = None) -> dict:
    """Send SMS via MSG91 API. Returns {'success': bool, 'ref': str, 'error': str}."""
    url = "https://api.msg91.com/api/v5/flow/"
    payload = {
        "template_id": template_id or "default",
        "short_url": "0",
        "recipients": [{"mobiles": f"91{mobile.lstrip('+').lstrip('91')}", "message": message}],
    }
    headers = {"authkey": auth_key or "", "content-type": "application/JSON"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("type") == "success":
            return {"success": True, "ref": data.get("request_id", ""), "error": ""}
        return {"success": False, "ref": "", "error": str(data)}
    except Exception as e:
        logger.error("MSG91 SMS error: %s", e)
        return {"success": False, "ref": "", "error": str(e)}


# --- Twilio -------------------------------------------------------------------

def send_sms_twilio(mobile: str, message: str, account_sid: str, auth_token: str, from_number: str) -> dict:
    """Send SMS via Twilio REST API."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        resp = requests.post(url, data={
            "To": f"+91{mobile.lstrip('+').lstrip('91')}",
            "From": from_number,
            "Body": message,
        }, auth=(account_sid, auth_token), timeout=10)
        data = resp.json()
        if resp.status_code in (200, 201):
            return {"success": True, "ref": data.get("sid", ""), "error": ""}
        return {"success": False, "ref": "", "error": data.get("message", str(data))}
    except Exception as e:
        logger.error("Twilio SMS error: %s", e)
        return {"success": False, "ref": "", "error": str(e)}


# --- WhatsApp (Meta Cloud API) -------------------------------------------------

def send_whatsapp_message(mobile: str, message: str, access_token: str, phone_number_id: str) -> dict:
    """Send WhatsApp text message via Meta Cloud API."""
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": f"91{mobile.lstrip('+').lstrip('91')}",
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            msg_id = data.get("messages", [{}])[0].get("id", "")
            return {"success": True, "ref": msg_id, "error": ""}
        return {"success": False, "ref": "", "error": str(data)}
    except Exception as e:
        logger.error("WhatsApp API error: %s", e)
        return {"success": False, "ref": "", "error": str(e)}


# --- High-level helpers --------------------------------------------------------

def _log_notification(patient, channel, mobile, message, result, report=None):
    from .models import NotificationLog
    NotificationLog.objects.create(
        patient=patient,
        channel=channel,
        mobile=mobile,
        message=message,
        status='sent' if result['success'] else 'failed',
        provider_ref=result.get('ref', ''),
        error_msg=result.get('error', ''),
        related_report=report,
    )


def send_report_ready_sms(report) -> bool:
    """
    Send 'report ready' SMS to patient. Called from signals.py on is_finalized.
    Returns True if sent successfully.
    """
    s = _get_settings()
    patient = report.booking.patient
    mobile = patient.mobile
    if not mobile:
        return False

    lab_name = s.lab_name or "Indian Path-Lab"
    message = (
        f"Namaste {patient.first_name}, aapki {report.test.name} report taiyar hai. "
        f"Report No: {report.report_id}. "
        f"Lab: {lab_name}. "
        f"Kisi bhi jaankari ke liye hum se sampark karein."
    )

    provider = getattr(s, 'sms_provider', 'none')
    result = {"success": False, "ref": "", "error": "No provider configured"}

    if provider == 'msg91' and getattr(s, 'msg91_auth_key', ''):
        result = send_sms_msg91(
            mobile, message,
            template_id=getattr(s, 'msg91_template_id', ''),
            auth_key=s.msg91_auth_key,
            sender_id=getattr(s, 'msg91_sender_id', 'IPLABS'),
        )
    elif provider == 'twilio' and getattr(s, 'twilio_account_sid', ''):
        result = send_sms_twilio(
            mobile, message,
            account_sid=s.twilio_account_sid,
            auth_token=s.twilio_auth_token,
            from_number=s.twilio_from_number,
        )

    _log_notification(patient, 'sms', mobile, message, result, report)

    # WhatsApp bhi bhejo agar enabled hai
    if getattr(s, 'whatsapp_enabled', False) and getattr(s, 'whatsapp_token', ''):
        wa_result = send_whatsapp_message(
            mobile, message,
            access_token=s.whatsapp_token,
            phone_number_id=s.whatsapp_phone_id,
        )
        _log_notification(patient, 'whatsapp', mobile, message, wa_result, report)

    return result['success']


def send_booking_confirmation_sms(booking) -> bool:
    """Send booking confirmation SMS."""
    s = _get_settings()
    patient = booking.patient
    mobile = patient.mobile
    if not mobile:
        return False

    tests_str = ", ".join(t.name for t in booking.tests.all()[:3])
    message = (
        f"Namaste {patient.first_name}, aapki booking confirm ho gayi. "
        f"Receipt: {booking.receipt_id}. Tests: {tests_str}. "
        f"Total: Rs.{booking.total}. "
        f"{s.lab_name or 'Indian Path-Lab'}"
    )

    provider = getattr(s, 'sms_provider', 'none')
    result = {"success": False, "ref": "", "error": "No provider configured"}

    if provider == 'msg91' and getattr(s, 'msg91_auth_key', ''):
        result = send_sms_msg91(mobile, message, auth_key=s.msg91_auth_key)
    elif provider == 'twilio' and getattr(s, 'twilio_account_sid', ''):
        result = send_sms_twilio(mobile, message, s.twilio_account_sid, s.twilio_auth_token, s.twilio_from_number)

    _log_notification(patient, 'sms', mobile, message, result)
    return result['success']
