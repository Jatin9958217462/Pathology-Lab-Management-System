"""
context_processors.py
---------------------
Django context processors for the PathLab application.

These functions inject global variables into every template context,
so templates can access lab info, user role, and app version without
explicit view-level passing.
"""

from django.conf import settings as django_settings


def lab_context(request):
    """
    Injects lab-wide context into every template:
    - user_role     : current user's role (admin / staff / doctor / patient / anonymous)
    - LAB_NAME      : lab name from LabSettings
    - LAB_PHONE     : lab phone from LabSettings
    - LAB           : full LabSettings object (for logo, address, etc.)
    - APP_VERSION   : application version string (from settings.py)
    """
    # -- Determine user role ---------------------------------------------------
    role = 'anonymous'
    if request.user.is_authenticated:
        try:
            role = request.user.profile.role
        except Exception:
            role = 'patient'

    # -- Load lab settings (singleton) ----------------------------------------
    try:
        from .models import LabSettings
        lab = LabSettings.get()
    except Exception:
        lab = None

    lab_name  = lab.lab_name if lab else 'Indian Path-Lab'
    lab_phone = lab.phone    if lab else '9213303786, 9971404170'

    # -- App version from settings.py ------------------------------------------
    app_version = getattr(django_settings, 'APP_VERSION_NAME', 'PathLab v1.1')

    return {
        'user_role':   role,
        'LAB_NAME':    lab_name,
        'LAB_PHONE':   lab_phone,
        'LAB':         lab,
        'APP_VERSION': app_version,
    }
