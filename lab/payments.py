"""
Razorpay Payment Gateway Integration
======================================
Setup:
  1. pip install razorpay
  2. Add in LabSettings: razorpay_key_id, razorpay_key_secret
  3. Add RAZORPAY_WEBHOOK_SECRET in settings.py for webhook verification

URLs needed (already added in urls.py):
  /payment/create-order/<booking_pk>/   -> payment_create_order
  /payment/verify/                       -> payment_verify
  /payment/webhook/                      -> payment_webhook (CSRF exempt)
"""
import hashlib
import hmac
import json
import logging

logger = logging.getLogger(__name__)


def get_razorpay_client():
    """Return initialized Razorpay client using LabSettings keys."""
    try:
        import razorpay
    except ImportError:
        raise ImportError("Razorpay not installed. Run: pip install razorpay")

    from .models import LabSettings
    s = LabSettings.get()
    key_id     = getattr(s, 'razorpay_key_id', '')
    key_secret = getattr(s, 'razorpay_key_secret', '')
    if not key_id or not key_secret:
        raise ValueError("Razorpay keys not configured in Lab Settings.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(booking):
    """
    Create Razorpay order for a booking.
    Returns (PaymentOrder instance, razorpay_order dict) or raises.
    """
    from .models import PaymentOrder
    client = get_razorpay_client()

    amount_paise = int(booking.due * 100)   # Razorpay takes paise
    rz_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": booking.receipt_id,
        "notes": {
            "patient_name": booking.patient.full_name,
            "patient_mobile": booking.patient.mobile,
        },
    })

    po = PaymentOrder.objects.create(
        booking=booking,
        razorpay_order_id=rz_order['id'],
        amount=booking.due,
        status='created',
    )
    return po, rz_order


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Verify Razorpay payment signature. Returns True if valid."""
    from .models import LabSettings
    s = LabSettings.get()
    key_secret = getattr(s, 'razorpay_key_secret', '').encode()
    body = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected = hmac.new(key_secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)


def handle_payment_success(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Called after successful payment. Updates PaymentOrder + Booking.
    Returns True on success.
    """
    from .models import PaymentOrder
    from django.utils import timezone

    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning("Razorpay signature verification FAILED for order %s", razorpay_order_id)
        return False

    try:
        po = PaymentOrder.objects.get(razorpay_order_id=razorpay_order_id)
        po.razorpay_payment_id = razorpay_payment_id
        po.razorpay_signature  = razorpay_signature
        po.status  = 'paid'
        po.paid_at = timezone.now()
        po.save()

        # Update booking paid amount
        booking = po.booking
        booking.paid = booking.paid + po.amount
        booking.due  = max(0, booking.total - booking.paid)
        if booking.due == 0:
            booking.payment_mode = 'Online/Razorpay'
        booking.save()

        logger.info("Payment success: order=%s payment=%s amount=%.2f", razorpay_order_id, razorpay_payment_id, po.amount)
        return True
    except PaymentOrder.DoesNotExist:
        logger.error("PaymentOrder not found for order_id: %s", razorpay_order_id)
        return False
    except Exception as e:
        logger.error("Payment handling error: %s", e)
        return False
