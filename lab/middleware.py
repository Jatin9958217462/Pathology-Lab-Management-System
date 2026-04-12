"""
middleware.py -- PathLab v1.1
===============================================================================
Custom Django middleware for the PathLab application.

ProSuiteMiddleware
  Protects advanced / financial feature URLs with a PIN unlock.
  Users must enter the Pro Suite PIN (configured in LabSettings) once per
  session to access protected routes like Payments, Settings, Staff, etc.

  Flow:
    1. Request comes in for a protected URL
    2. Check session for 'pro_suite_unlocked' flag
    3. If not unlocked -> redirect to pro_suite_lock page (shows PIN form)
    4. After correct PIN -> set session flag and redirect to original URL
    5. Subsequent requests pass through without re-entering PIN

  Exempt:
    - POST endpoints like /settings/save/ are exempt (user already unlocked
      to reach the form, no need to re-check)
    - The lock page itself (/pro-suite-lock/) is exempt to avoid redirect loops

VERSION: 1.1
===============================================================================
"""
from django.shortcuts import redirect
from django.conf import settings


PRO_SUITE_URLS = getattr(settings, 'PRO_SUITE_URLS', [
    '/payments/', '/insurance/', '/notifications/', '/branches/',
    '/analyser/', '/hl7/', '/revenue/', '/expenditures/',
    '/inventory/', '/qc-log/', '/critical-alerts/', '/commissions/',
    '/home-collections/', '/settings/', '/staff/',
])

# POST-only save endpoints that should be allowed even without unlock
# (the form is already on a locked page, so the user got there after unlock)
PRO_SUITE_EXEMPT_POSTS = [
    '/settings/save/',
    '/staff/',          # POST to add/delete/reset pass
]


class ProSuiteMiddleware:
    """Require PIN unlock for Pro Suite URLs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Check if this path is in Pro Suite
        is_pro = any(path.startswith(u) for u in PRO_SUITE_URLS)

        if is_pro and request.user.is_authenticated:
            # Allow POST to save/action endpoints without re-checking lock
            if request.method == 'POST' and any(path.startswith(e) for e in PRO_SUITE_EXEMPT_POSTS):
                pass  # Let through
            elif not request.session.get('pro_suite_unlocked'):
                return redirect(f'/pro-suite/lock/?next={path}')

        return self.get_response(request)
