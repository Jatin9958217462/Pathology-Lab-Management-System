"""
signals.py -- PathLab v1.1
===============================================================================
Django signal handlers for automated background actions.

SIGNALS REGISTERED:
  post_save -> User        ensure_profile
    Creates a UserProfile whenever a new Django User is created.
    Superusers get 'admin' role, everyone else gets 'patient' by default.

  post_save -> Report      report_post_save
    Fires when a Report is saved. If it just became finalized (is_finalized
    toggled True), triggers:
      1. AI auto-interpretation (if enabled in LabSettings)
      2. SMS / WhatsApp notification to patient

  post_save -> Booking     booking_post_save
    Fires when any Booking is created or updated. If the booking has a
    ref_doctor, recalculates and upserts the DoctorCommission record
    for that doctor's current month. This keeps commissions always
    up-to-date without manual generation.

HOW AUTO-COMMISSION WORKS:
  1. Booking saved with ref_doctor + total amount
  2. _update_doctor_commission() runs
  3. All bookings for that doctor in that month are summed
  4. DoctorCommission.update_or_create() with new total + commission_amt
  5. Admin can still manually edit % from the Commissions page

VERSION: 1.1
===============================================================================
"""

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserProfile


# --- User Profile Auto-Creation ----------------------------------------------

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    """
    Automatically create or update UserProfile when a User is saved.
    - New user: create profile with role='admin' (superuser) or 'patient'
    - Existing user: ensure profile.save() is called (triggers unique_code gen)
    """
    if created:
        role = 'admin' if instance.is_superuser else 'patient'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        try:
            instance.profile.save()
        except UserProfile.DoesNotExist:
            role = 'admin' if instance.is_superuser else 'patient'
            UserProfile.objects.create(user=instance, role=role)


# --- Report Finalization Triggers --------------------------------------------

def _on_report_finalized(report):
    """
    Called once when a report transitions to is_finalized=True.
    Runs AI interpretation and sends SMS notification.
    Errors are logged but do not crash the save operation.
    """
    from .models import LabSettings
    s = LabSettings.get()

    # 1. AI Interpretation -- auto generate if enabled in settings
    if getattr(s, 'ai_auto_interpret', True):
        try:
            from .ai_interpretation import generate_interpretation
            generate_interpretation(report)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("AI interpretation error: %s", e)

    # 2. SMS / WhatsApp notification to patient
    try:
        from .notifications import send_report_ready_sms
        send_report_ready_sms(report)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("SMS notification error: %s", e)


# Track previously finalized state to detect the transition
_previously_finalized = {}


@receiver(post_save, sender='lab.Report')
def report_post_save(sender, instance, created, **kwargs):
    """
    Trigger AI + SMS when a report is finalized for the first time.
    Uses in-memory cache (_previously_finalized) to detect the
    False->True transition. Will re-trigger on server restart if
    reports were already finalized.
    """
    prev_finalized = _previously_finalized.get(instance.pk, False)
    if instance.is_finalized and not prev_finalized:
        _on_report_finalized(instance)
    _previously_finalized[instance.pk] = instance.is_finalized


# --- Auto Commission Update ---------------------------------------------------

def _update_doctor_commission(booking):
    """
    Recalculate and upsert the DoctorCommission for the booking's doctor
    and month. Called every time a Booking is saved.

    Algorithm:
      1. Get all bookings for this doctor in the booking's month
      2. Sum their totals
      3. Apply the referral_pct from the current booking
      4. update_or_create the DoctorCommission record
      5. Set the M2M bookings relation
    """
    try:
        import datetime
        from decimal import Decimal
        from .models import DoctorCommission, Booking

        # Skip if no doctor is assigned to this booking
        doctor = booking.ref_doctor
        if not doctor:
            return

        # Commission month = first day of the booking month
        bd = (booking.booking_date
              if hasattr(booking, 'booking_date') and booking.booking_date
              else booking.created_at.date())
        month_date = bd.replace(day=1)

        # Get ALL bookings for this doctor in this month
        bookings_qs = Booking.objects.filter(
            ref_doctor=doctor,
            booking_date__year=month_date.year,
            booking_date__month=month_date.month,
        )
        total = sum(b.total for b in bookings_qs)

        # Use referral_pct from the triggering booking (or 0 if not set)
        pct = float(booking.referral_pct or 0)
        comm_amt = Decimal(str(total)) * Decimal(str(pct)) / Decimal('100')

        # Upsert the commission record
        comm, _ = DoctorCommission.objects.update_or_create(
            doctor=doctor,
            month=month_date,
            defaults={
                'total_billing':  total,
                'commission_pct': pct,
                'commission_amt': comm_amt,
            }
        )
        # Update the bookings M2M relation
        comm.bookings.set(bookings_qs)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Auto commission update error: %s", e)


@receiver(post_save, sender='lab.Booking')
def booking_post_save(sender, instance, **kwargs):
    """Auto-update doctor commission whenever a Booking is created or updated."""
    _update_doctor_commission(instance)
