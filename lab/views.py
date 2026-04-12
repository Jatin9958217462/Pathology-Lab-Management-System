# -*- coding: utf-8 -*-
"""
views.py -- PathLab v1.1
===============================================================================
Main application views for the PathLab Laboratory Management System.

MODULE STRUCTURE:
  +-- Utility Functions        generate_qr_base64, etc.
  +-- Decorators               login_required wrappers for role-based access
  +-- Authentication           login, logout, register
  +-- Dashboard                main dashboard with stats
  +-- Patients                 CRUD for patient records
  +-- Bookings                 test booking management
  +-- Reports                  report entry, PDF, print, bulk operations
  +-- Doctors                  referring doctor management + portal access
  +-- Tests & Parameters       test catalog and parameter management
  +-- Staff & Users            staff/doctor user account management
  +-- Lab Settings             branding, margins, signatures, images
  +-- Patient Portal           my_reports for patients and doctors
  +-- Doctor Commissions       monthly commission tracking and slips
  +-- Advanced Search          cross-entity search
  +-- Landing Page             public-facing lab website
  +-- API / AJAX               JSON endpoints for dynamic UI

ROLE HIERARCHY:
  admin  > staff > doctor > patient > anonymous

VERSION: 1.1
AUTHOR:  IPL PathLab Development Team
===============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum
from functools import wraps
from decimal import Decimal
import json, datetime, base64, io

from .models import UserProfile, Patient, Doctor, Test, TestParameter, Booking, Report, ReportResult


def generate_qr_base64(data):
    """Generate a QR code for the given data and return as base64 PNG string."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        return ''


# --- Decorators --------------------------------------------------------------

def role_required(*roles):
    def dec(fn):
        @wraps(fn)
        def inner(request, *a, **kw):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                if request.user.profile.role not in roles and not request.user.is_superuser:
                    messages.error(request, "Access denied.")
                    return redirect('dashboard')
            except UserProfile.DoesNotExist:
                return redirect('login')
            return fn(request, *a, **kw)
        return inner
    return dec

admin_only   = role_required('admin')
staff_access = role_required('admin', 'staff')
doc_access   = role_required('admin', 'staff', 'doctor')

def get_role(request):
    try:    return request.user.profile.role
    except: return 'patient'


# --- Auth ---------------------------------------------------------------------

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('landing_page')

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        u = authenticate(request, username=request.POST.get('username',''),
                         password=request.POST.get('password',''))
        if u:
            login(request, u); return redirect(request.GET.get('next','dashboard'))
        messages.error(request, "Invalid username or password.")
    return render(request, 'lab/login.html')

def logout_view(request):
    logout(request); return redirect('login')

def register_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        uname = request.POST.get('username','').strip()
        pw    = request.POST.get('password','').strip()
        pw2   = request.POST.get('password2','').strip()
        if User.objects.filter(username=uname).exists():
            messages.error(request, "Username already taken.")
        elif pw != pw2:
            messages.error(request, "Passwords do not match.")
        elif len(pw) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            u = User.objects.create_user(uname, request.POST.get('email',''), pw,
                first_name=request.POST.get('first_name',''),
                last_name=request.POST.get('last_name',''))
            UserProfile.objects.get_or_create(user=u, defaults={'role':'patient'})
            login(request, u)
            return redirect('dashboard')
    return render(request, 'lab/register.html')


# --- Dashboard ----------------------------------------------------------------

@login_required
def dashboard(request):
    """
    Main dashboard -- shows lab-wide statistics and quick-access panels.

    Stats provided:
    - Patient count, doctor count, total reports
    - Today's bookings and revenue
    - Monthly revenue (current month)
    - Reports: pending (not finalized) vs finalized today
    - Top 5 most-booked tests this month
    - Recent bookings (last 8)
    - Pending reports awaiting entry (last 8)
    - Critical alerts count (unacknowledged)
    """
    role = get_role(request)
    if role == 'patient':
        return redirect('my_reports')

    today      = datetime.date.today()
    month_start = today.replace(day=1)

    # -- Core counts -----------------------------------------------------------
    total_patients  = Patient.objects.count()
    total_reports   = Report.objects.count()
    total_doctors   = Doctor.objects.count()
    today_bookings  = Booking.objects.filter(booking_date=today).count()

    # -- Revenue stats ---------------------------------------------------------
    revenue_today   = Booking.objects.filter(booking_date=today).aggregate(r=Sum('total'))['r'] or 0
    revenue_month   = Booking.objects.filter(booking_date__gte=month_start).aggregate(r=Sum('total'))['r'] or 0
    revenue_all     = Booking.objects.aggregate(r=Sum('total'))['r'] or 0

    # -- Report status ---------------------------------------------------------
    pending_count   = Report.objects.filter(is_finalized=False).count()
    finalized_today = Report.objects.filter(is_finalized=True, report_date=today).count()

    # -- Top 5 tests this month (by booking count) -----------------------------
    from django.db.models import Count
    top_tests = (
        Booking.objects
        .filter(booking_date__gte=month_start)
        .values('tests__name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:5]
    )

    # -- Critical alerts (unacknowledged) -------------------------------------
    try:
        from .models import CriticalAlert
        critical_count = CriticalAlert.objects.filter(acknowledged=False).count()
    except Exception:
        critical_count = 0

    ctx = {
        'role': role,
        'today': today,
        # Counts
        'total_patients':  total_patients,
        'total_reports':   total_reports,
        'total_doctors':   total_doctors,
        'today_bookings':  today_bookings,
        'pending_count':   pending_count,
        'finalized_today': finalized_today,
        'critical_count':  critical_count,
        # Revenue
        'revenue_today':   revenue_today,
        'revenue_month':   revenue_month,
        'revenue_all':     revenue_all,
        # Lists
        'top_tests':        top_tests,
        'recent_bookings':  Booking.objects.select_related('patient','ref_doctor').order_by('-created_at')[:8],
        'pending_reports':  Report.objects.filter(is_finalized=False).select_related('booking__patient','test')[:8],
    }
    return render(request, 'lab/dashboard.html', ctx)



# --- Patients -----------------------------------------------------------------

@login_required
@doc_access
def patients_list(request):
    """List all patients with real-time search across name, mobile, ID, doctor."""
    q = request.GET.get('q','')
    qs = Patient.objects.select_related('referring_doctor').all()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(mobile__icontains=q) | Q(patient_id__icontains=q) |
            Q(email__icontains=q) | Q(custom_display_id__icontains=q) |
            Q(referring_doctor__name__icontains=q)
        )
    return render(request, 'lab/patients.html', {
        'patients': qs, 'q': q, 'role': get_role(request),
        'doctors': Doctor.objects.all(),
    })

@login_required
@staff_access
def patient_add(request):
    if request.method == 'POST':
        fn = request.POST.get('first_name','').strip()
        ln = request.POST.get('last_name','').strip()
        age= request.POST.get('age','0').strip()
        mob= request.POST.get('mobile','').strip()
        if not fn or not age:
            messages.error(request, "First name and age are required.")
            return redirect('patients')
        doc_id = request.POST.get('ref_doctor','')
        doc = Doctor.objects.filter(pk=doc_id).first() if doc_id else None
        pt = Patient(first_name=fn, last_name=ln, age=int(age), mobile=mob,
            honorific=request.POST.get('honorific','Mr.'),
            age_unit=request.POST.get('age_unit','Years'),
            gender=request.POST.get('gender','Male'),
            email=request.POST.get('email',''),
            address=request.POST.get('address',''),
            blood_group=request.POST.get('blood_group',''),
            priority=request.POST.get('priority','Normal'),
            referring_doctor=doc)
        if request.FILES.get('photo'): pt.photo = request.FILES['photo']
        pt.save()
        messages.success(request, f"Patient registered: {pt.full_name} -- ID: {pt.patient_id}")
        return redirect('patients')
    return redirect('patients')

@login_required
@staff_access
def patient_edit(request, pk):
    pt = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        pt.honorific  = request.POST.get('honorific', pt.honorific)
        pt.first_name = request.POST.get('first_name', pt.first_name)
        pt.last_name  = request.POST.get('last_name',  pt.last_name)
        pt.age        = request.POST.get('age', pt.age)
        pt.gender     = request.POST.get('gender', pt.gender)
        pt.age_unit   = request.POST.get('age_unit', pt.age_unit)
        pt.mobile     = request.POST.get('mobile', pt.mobile)
        pt.email      = request.POST.get('email', pt.email)
        pt.address    = request.POST.get('address', pt.address)
        pt.blood_group= request.POST.get('blood_group', pt.blood_group)
        pt.priority   = request.POST.get('priority', pt.priority)
        doc_id = request.POST.get('ref_doctor','')
        pt.referring_doctor = Doctor.objects.filter(pk=doc_id).first() if doc_id else None
        if request.FILES.get('photo'): pt.photo = request.FILES['photo']
        pt.save()
        messages.success(request, "Patient updated.")
    return redirect('patients')

@login_required
@admin_only
def patient_delete(request, pk):
    get_object_or_404(Patient, pk=pk).delete()
    messages.success(request, "Patient deleted.")
    return redirect('patients')


# --- Booking ------------------------------------------------------------------

@login_required
@staff_access
def booking_new(request, pt_pk=None):
    """New booking / patient visit -- select patient + tests + billing."""
    patients = Patient.objects.all().order_by('-registered_at')
    doctors  = Doctor.objects.all()
    tests    = Test.objects.filter(active=True).order_by('category','name')

    selected_pt = None
    if pt_pk:
        selected_pt = get_object_or_404(Patient, pk=pt_pk)

    if request.method == 'POST':
        pt_id    = request.POST.get('patient_id','')
        test_ids = request.POST.getlist('test_ids')
        if not pt_id:
            messages.error(request, "Please select a patient.")
            return redirect('booking_new')
        patient  = get_object_or_404(Patient, pk=pt_id)
        sel_tests= Test.objects.filter(pk__in=test_ids, active=True)
        if not sel_tests.exists():
            messages.error(request, "Please select at least one test.")
            return redirect('booking_new')

        doc_id = request.POST.get('ref_doctor','')
        doc = Doctor.objects.filter(pk=doc_id).first() if doc_id else patient.referring_doctor

        booking = Booking.objects.create(
            patient=patient, ref_doctor=doc,
            booking_date=request.POST.get('booking_date') or datetime.date.today(),
            sample_date=request.POST.get('sample_date') or datetime.date.today(),
            status='sample_collected',
            discount_pct=Decimal(request.POST.get('discount_pct','0') or '0'),
            referral_pct=Decimal(request.POST.get('referral_pct','0') or '0'),
            paid=Decimal(request.POST.get('paid','0') or '0'),
            payment_mode=request.POST.get('payment_mode','Cash'),
            created_by=request.user,
        )
        booking.tests.set(sel_tests)
        booking.recalculate()

        # Auto-create one Report per test
        for t in sel_tests:
            rpt = Report.objects.create(booking=booking, test=t, report_date=booking.sample_date)
            # Pre-populate results from TestParameters
            for i, param in enumerate(t.parameters.all()):
                ReportResult.objects.create(
                    report=rpt, parameter=param,
                    param_name=param.param_name, unit=param.unit,
                    lower_limit=param.lower_limit, upper_limit=param.upper_limit,
                    sort_order=i,
                )

        messages.success(request, f"Booking created: {booking.receipt_id} -- {patient.full_name}")
        return redirect('booking_detail', pk=booking.pk)

    from .models import TestProfile
    profiles = TestProfile.objects.filter(is_active=True).prefetch_related('tests').order_by('sort_order','name')
    import json as _json
    doctors_json = _json.dumps([{'pk': d.pk, 'name': d.name, 'doc_id': d.doc_id} for d in doctors])
    return render(request, 'lab/booking_new.html', {
        'patients': patients, 'doctors': doctors, 'tests': tests,
        'profiles': profiles,
        'selected_pt': selected_pt, 'role': get_role(request),
        'today': datetime.date.today().isoformat(),
        'doctors_json': doctors_json,
    })

@login_required
@doc_access
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests','reports__results','reports__test'),
        pk=pk)
    return render(request, 'lab/booking_detail.html', {
        'booking': booking, 'reports': booking.reports.all(), 'role': get_role(request),
    })

@login_required
@staff_access
def booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        booking.status = request.POST.get('status', booking.status)
        booking.save()
        messages.success(request, "Status updated.")
    return redirect('booking_detail', pk=pk)

@login_required
@doc_access
def bill_pdf(request, pk):
    """Bill with letterhead -- PDF only."""
    from .models import LabSettings
    booking = get_object_or_404(Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests'), pk=pk)
    lab = LabSettings.get()
    return render(request, 'lab/bill_pdf.html', {'booking': booking, 'letterhead': True, 'lab': lab})

@login_required
@doc_access
def bill_print(request, pk):
    """Bill Print - uses bill print margins from Lab Settings."""""
    from .models import LabSettings
    booking = get_object_or_404(Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests'), pk=pk)
    lab = LabSettings.get()
    return render(request, 'lab/bill_pdf.html', {'booking': booking, 'letterhead': False, 'lab': lab})


# --- Report Entry -------------------------------------------------------------

@login_required
@staff_access
def report_entry(request, report_pk):
    """Enter / edit readings for one test report."""
    report  = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    results = report.results.all()
    role    = get_role(request)

    # Staff can only view, not edit results
    if role == 'staff':
        messages.error(request, "Staff members cannot edit test results. Contact admin.")
        return redirect('booking_detail', pk=report.booking.pk)

    if request.method == 'POST':
        for res in results:
            val = request.POST.get(f'val_{res.pk}', '').strip()
            # Use default_value if no reading entered and default exists
            if not val and res.parameter and res.parameter.default_value:
                val = res.parameter.default_value
            res.value = val
            res.flag  = res.compute_flag()
            res.save()
        report.remarks = request.POST.get('remarks','')
        report.custom_report_no = request.POST.get('custom_report_no','').strip()
        # Custom dates
        for field in ['sample_drawn_date','sample_received_date','result_reported_date']:
            val = request.POST.get(field,'').strip()
            setattr(report, field, val if val else None)
        # Save custom_display_id to patient
        cdi = request.POST.get('custom_display_id','').strip()
        if cdi:
            report.booking.patient.custom_display_id = cdi
            report.booking.patient.save(update_fields=['custom_display_id'])
        action = request.POST.get('action','save')
        if action == 'finalize':
            report.is_finalized = True
        report.save()
        messages.success(request, f"Report {report.report_id} saved.")
        return redirect('booking_detail', pk=report.booking.pk)

    return render(request, 'lab/report_entry.html', {
        'report': report, 'results': results, 'role': role,
        'booking': report.booking,
    })

@login_required
def report_view(request, report_pk):
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    role = get_role(request)
    # Patient can only see their own
    if role == 'patient':
        try:
            if report.booking.patient != request.user.patient_profile:
                messages.error(request, "Access denied."); return redirect('my_reports')
        except Patient.DoesNotExist:
            return redirect('my_reports')
    # If accessed via QR scan (from a non-logged-in context or direct link), redirect to all-reports bulk PDF
    if request.GET.get('qr') == '1':
        patient = report.booking.patient
        all_report_ids = Report.objects.filter(
            booking__patient=patient, is_finalized=True
        ).values_list('pk', flat=True)
        ids_qs = '&'.join(f'ids={pk}' for pk in all_report_ids)
        return redirect(f'/reports/bulk-pdf/?{ids_qs}&qr_source=1')
    return render(request, 'lab/report_view.html', {
        'report': report, 'results': report.results.all(), 'role': role,
    })

@login_required
def report_pdf(request, report_pk):
    """Report WITH letterhead (for PDF/download)."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    role = get_role(request)
    if role == 'patient':
        try:
            if report.booking.patient != request.user.patient_profile:
                return HttpResponse("Access denied", status=403)
        except Patient.DoesNotExist:
            return HttpResponse("Access denied", status=403)
    from .models import LabSettings
    lab = LabSettings.get()
    qr_url = request.build_absolute_uri(f'/report/{report_pk}/view/?qr=1')
    qr_b64 = generate_qr_base64(qr_url)
    return render(request, 'lab/report_pdf.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab, 'qr_b64': qr_b64})

@login_required
@doc_access
def report_print_direct(request, report_pk):
    """Direct Print - uses print margins from Lab Settings, NO letterhead."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    qr_b64 = generate_qr_base64(request.build_absolute_uri(f'/report/{report_pk}/view/'))
    return render(request, 'lab/report_print.html', {'report': report, 'results': report.results.all(), 'letterhead': False, 'lab': lab, 'qr_b64': qr_b64})

@login_required
@doc_access
def report_print_margins(request, report_pk):
    """Print WITH letterhead - uses print margins from Lab Settings."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    qr_b64 = generate_qr_base64(request.build_absolute_uri(f'/report/{report_pk}/view/'))
    return render(request, 'lab/report_print.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab, 'qr_b64': qr_b64})

@login_required
@doc_access
def report_pdf_zero(request, report_pk):
    """PDF -- zero top/bottom margins (full bleed for digital/WhatsApp sharing)."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    qr_b64 = generate_qr_base64(request.build_absolute_uri(f'/report/{report_pk}/view/'))
    return render(request, 'lab/report_pdf.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab, 'qr_b64': qr_b64})

@login_required
@staff_access
def report_finalize(request, report_pk):
    report = get_object_or_404(Report, pk=report_pk)
    report.is_finalized = True
    report.save()
    messages.success(request, f"Report {report.report_id} finalized.")
    return redirect('booking_detail', pk=report.booking.pk)

@login_required
@staff_access
def result_inline_edit(request, result_pk):
    """AJAX: Edit a single ReportResult param_name, unit, lower_limit, upper_limit inline."""
    from .models import ReportResult
    from django.http import JsonResponse
    # Staff cannot edit results
    if get_role(request) == 'staff':
        return JsonResponse({'ok': False, 'error': 'Staff not allowed to edit results'}, status=403)
    result = get_object_or_404(ReportResult, pk=result_pk)
    if request.method == 'POST':
        result.param_name  = request.POST.get('param_name', result.param_name).strip() or result.param_name
        result.unit        = request.POST.get('unit', result.unit).strip()
        lo = request.POST.get('lower_limit', '').strip()
        hi = request.POST.get('upper_limit', '').strip()
        result.lower_limit = float(lo) if lo else None
        result.upper_limit = float(hi) if hi else None
        result.flag = result.compute_flag()
        result.save()
        return JsonResponse({'ok': True, 'flag': result.flag,
                             'param_name': result.param_name,
                             'unit': result.unit,
                             'lower_limit': result.lower_limit,
                             'upper_limit': result.upper_limit})
    return JsonResponse({'ok': False}, status=400)

@login_required
@admin_only
def report_delete(request, report_pk):
    report = get_object_or_404(Report, pk=report_pk)
    bk_pk = report.booking.pk
    report.delete()
    messages.success(request, "Report deleted.")
    return redirect('booking_detail', pk=bk_pk)

@login_required
@doc_access
def reports_list(request):
    """List all reports with search across report ID, patient, doctor, test name."""
    q = request.GET.get('q','')
    qs = Report.objects.select_related('booking__patient','booking__ref_doctor','test').order_by('-created_at')
    if q:
        qs = qs.filter(
            Q(report_id__icontains=q) |
            Q(booking__patient__first_name__icontains=q) |
            Q(booking__patient__last_name__icontains=q) |
            Q(booking__patient__mobile__icontains=q) |
            Q(booking__patient__patient_id__icontains=q) |
            Q(booking__ref_doctor__name__icontains=q) |
            Q(test__name__icontains=q)
        ).distinct()
    return render(request, 'lab/reports_list.html', {'reports': qs, 'q': q, 'role': get_role(request)})


# --- Doctors ------------------------------------------------------------------

@login_required
@admin_only
def staff_list(request):
    """List all staff and doctor users."""
    from .models import UserProfile
    staff_users = UserProfile.objects.filter(role__in=['staff','doctor']).select_related('user')
    return render(request, 'lab/staff_users.html', {'staff_users': staff_users, 'role': get_role(request)})

@login_required
@admin_only
def staff_add(request):
    """Admin adds a staff or doctor user with mobile & password."""
    if request.method == 'POST':
        full_name = request.POST.get('full_name','').strip()
        mobile    = request.POST.get('mobile','').strip()
        password  = request.POST.get('password','').strip()
        role      = request.POST.get('role','staff')
        if not full_name or not mobile or not password:
            messages.error(request, "Full name, mobile, and password are required.")
            return redirect('staff_list')
        if role not in ('staff', 'doctor'):
            messages.error(request, "Invalid role.")
            return redirect('staff_list')
        # Username = mobile number
        if User.objects.filter(username=mobile).exists():
            messages.error(request, f"A user with mobile {mobile} already exists.")
            return redirect('staff_list')
        try:
            user = User.objects.create_user(username=mobile, password=password)
            user.first_name = full_name
            user.save()
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': role, 'phone': mobile}
            )
            if not created:
                profile.role = role
                profile.phone = mobile
                profile.save()
            messages.success(request, f"{'Staff' if role == 'staff' else 'Doctor'} '{full_name}' added. Access Code: {profile.unique_code}")
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
    return redirect('staff_list')

@login_required
@admin_only
def staff_delete(request, pk):
    from .models import UserProfile
    profile = get_object_or_404(UserProfile, pk=pk)
    name = profile.user.get_full_name() or profile.user.username
    profile.user.delete()
    messages.success(request, f"User '{name}' deleted.")
    return redirect('staff_list')

@login_required
@admin_only
def staff_reset_password(request, pk):
    """Admin resets a staff/doctor password."""
    from .models import UserProfile
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        new_pw = request.POST.get('password','').strip()
        if not new_pw:
            messages.error(request, "Password cannot be empty.")
            return redirect('staff_list')
        profile.user.set_password(new_pw)
        profile.user.save()
        messages.success(request, f"Password updated for {profile.user.first_name or profile.user.username}.")
    return redirect('staff_list')

@login_required
@doc_access
def doctors_list(request):
    """List all referring doctors. Admin can connect/disconnect portal access."""
    return render(request, 'lab/doctors.html', {'doctors': Doctor.objects.all(), 'role': get_role(request), 'user_role': get_role(request)})

@login_required
@staff_access
def doctor_add(request):
    """Add a new referring doctor to the master list."""
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        mob  = request.POST.get('mobile','').strip()
        if not name or not mob:
            messages.error(request, "Name and mobile required."); return redirect('doctors')
        Doctor.objects.create(name=name, qualification=request.POST.get('qualification',''),
            specialization=request.POST.get('specialization',''), mobile=mob,
            email=request.POST.get('email',''), hospital=request.POST.get('hospital',''),
            address=request.POST.get('address',''))
        messages.success(request, f"Dr. {name} added.")
    return redirect('doctors')

@login_required
@admin_only
def doctor_delete(request, pk):
    get_object_or_404(Doctor, pk=pk).delete()
    messages.success(request, "Doctor removed.")
    return redirect('doctors')


@login_required
@admin_only
def doctor_connect(request, pk):
    """Link a Doctor record to a portal user account."""
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('doctors')
        # If user already exists, just link (don't recreate)
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_user(username=username, password=password)
            user.first_name = doctor.name
            user.save()
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'doctor', 'phone': doctor.mobile})
        # Ensure role is doctor
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'doctor'})
        if profile.role != 'doctor':
            profile.role = 'doctor'
            profile.save()
        doctor.linked_user = user
        doctor.save()
        messages.success(request, f"Dr. {doctor.name} linked to username '{username}'. They can now login to see their referred patients' reports.")
    return redirect('doctors')


@login_required
@admin_only
def doctor_disconnect(request, pk):
    """Unlink a Doctor from their portal user account."""
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.linked_user = None
    doctor.save()
    messages.success(request, f"Dr. {doctor.name} portal access removed.")
    return redirect('doctors')



# --- Tests --------------------------------------------------------------------

@login_required
def tests_list(request):
    q = request.GET.get('q','').strip()
    tests = Test.objects.filter(active=True).prefetch_related('parameters')
    if q:
        tests = tests.filter(Q(name__icontains=q) | Q(full_name__icontains=q))
    by_cat = {}
    for t in tests.order_by('category','name'):
        by_cat.setdefault(t.category, []).append(t)
    return render(request, 'lab/tests.html', {'by_cat': by_cat, 'role': get_role(request), 'user_role': get_role(request), 'q': q})

@login_required
@admin_only
def test_add(request):
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        price= request.POST.get('price','0')
        if not name: messages.error(request, "Test name required."); return redirect('tests')
        Test.objects.create(name=name, category=request.POST.get('category','Haematology'),
            price=Decimal(price or '0'), sample=request.POST.get('sample','Blood (Plain)'),
            tat=request.POST.get('tat',''))
        messages.success(request, f"Test '{name}' added.")
    return redirect('tests')

@login_required
@admin_only
def test_delete(request, pk):
    t = get_object_or_404(Test, pk=pk); t.active = False; t.save()
    messages.success(request, "Test removed.")
    return redirect('tests')

@login_required
@admin_only
def test_params(request, pk):
    """Manage reference parameters for a test."""
    test   = get_object_or_404(Test, pk=pk)
    params = test.parameters.all()
    if request.method == 'POST':
        action = request.POST.get('action','')
        if action == 'add':
            TestParameter.objects.create(
                test=test,
                param_name=request.POST.get('param_name','').strip(),
                unit=request.POST.get('unit','').strip(),
                lower_limit=request.POST.get('lower_limit') or None,
                upper_limit=request.POST.get('upper_limit') or None,
                is_text=bool(request.POST.get('is_text','')),
                test_method=request.POST.get('test_method','').strip(),
                default_value=request.POST.get('default_value','').strip(),
                sort_order=params.count(),
            )
            messages.success(request, "Parameter added.")
        elif action == 'delete':
            TestParameter.objects.filter(pk=request.POST.get('param_pk'), test=test).delete()
            messages.success(request, "Parameter deleted.")
        elif action == 'edit_param':
            # Inline param editing -- does NOT touch existing ReportResult records (denormalized)
            param = TestParameter.objects.filter(pk=request.POST.get('param_pk'), test=test).first()
            if param:
                param.param_name  = request.POST.get('param_name', param.param_name).strip() or param.param_name
                param.unit        = request.POST.get('unit', '').strip()
                lower = request.POST.get('lower_limit','').strip()
                upper = request.POST.get('upper_limit','').strip()
                param.lower_limit = float(lower) if lower else None
                param.upper_limit = float(upper) if upper else None
                param.is_text     = bool(request.POST.get('is_text',''))
                param.default_value = request.POST.get('default_value','').strip()
                param.save()
                messages.success(request, "Parameter updated.")
        elif action == 'edit_test':
            # Edit test short name and full display name
            new_name = request.POST.get('test_name','').strip()
            full_name = request.POST.get('test_full_name','').strip()
            if new_name:
                test.name = new_name
            test.full_name = full_name
            test.save()
            messages.success(request, "Test name updated.")
        return redirect('test_params', pk=pk)
    return render(request, 'lab/test_params.html', {'test': test, 'params': params, 'role': get_role(request), 'user_role': get_role(request)})

def rate_list(request):
    q = request.GET.get('q','').strip()
    tests = Test.objects.filter(active=True).order_by('category','name')
    if q:
        tests = tests.filter(name__icontains=q)
    by_cat = {}
    for t in tests:
        by_cat.setdefault(t.category, []).append(t)
    return render(request, 'lab/rate_list.html', {'by_cat': by_cat, 'q': q})


# --- Patient Portal -----------------------------------------------------------

@login_required
def my_reports(request):
    """
    Patient / Doctor self-service portal.
    - Patients see their own finalized reports.
    - Doctors see all finalized reports for their referred patients,
      grouped by patient with bulk-download option.
    """
    role = get_role(request)
    if role == 'doctor':
        try:
            # Doctor linked via Doctor.linked_user  (preferred)
            doctor_obj = Doctor.objects.filter(linked_user=request.user).first()
            if doctor_obj:
                reports = Report.objects.filter(
                    is_finalized=True,
                    booking__ref_doctor=doctor_obj
                ).select_related('test','booking','booking__patient','booking__ref_doctor')
            else:
                # Fallback: match by mobile == username
                reports = Report.objects.filter(
                    is_finalized=True,
                    booking__ref_doctor__mobile=request.user.username
                ).select_related('test','booking','booking__patient','booking__ref_doctor')
            return render(request, 'lab/my_reports.html', {
                'reports': reports, 'role': 'doctor',
                'doctor_obj': doctor_obj, 'patient': None
            })
        except Exception:
            return render(request, 'lab/my_reports.html', {'reports': [], 'role': 'doctor', 'patient': None})
    # Patient portal
    try:
        pt = request.user.patient_profile
        reports = Report.objects.filter(booking__patient=pt, is_finalized=True).select_related('test','booking')
        return render(request, 'lab/my_reports.html', {'patient': pt, 'reports': reports, 'role': 'patient'})
    except Patient.DoesNotExist:
        return render(request, 'lab/my_reports.html', {'patient': None, 'reports': [], 'role': 'patient'})


# --- AJAX ---------------------------------------------------------------------

@login_required
def api_patient(request, pk):
    pt = get_object_or_404(Patient, pk=pk)
    return JsonResponse({
        'id': pt.pk, 'patient_id': pt.patient_id, 'name': pt.full_name,
        'salutation': pt.salutation, 'honorific': pt.honorific,
        'age': pt.age, 'age_unit': pt.age_unit, 'gender': pt.gender,
        'mobile': pt.mobile, 'address': pt.address,
        'ref_doctor_id': pt.referring_doctor.pk if pt.referring_doctor else '',
        'ref_doctor_name': pt.referring_doctor.name if pt.referring_doctor else '',
    })

@login_required
def api_booking_tests(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    tests = [{'id': t.pk, 'name': t.name, 'price': str(t.price)} for t in booking.tests.all()]
    return JsonResponse({'tests': tests, 'total': str(booking.total)})


# --- Lab Settings ------------------------------------------------------------

@login_required
@admin_only
def lab_settings(request):
    from .models import LabSettings
    from django.conf import settings as django_settings
    settings = LabSettings.get()
    sig_fields = [
        ('signature_ansari', 'Dr. M. Ahmad Ansari'),
        ('signature_saleem', 'Dr. M. Saleem'),
        ('signature_kumar',  'N. Kumar'),
        ('signature_maurya', 'Dr. V.P. Maurya'),
    ]
    margins_groups = [
        ('Single Report',  'print', 'single'),
        ('Bulk Reports',   'print', 'bulk'),
        ('Bill / Invoice', 'print', 'bill'),
    ]
    margins_types = [
        ('🖨️ Print Margins', 'print', 'print'),
        ('📄 PDF Margins',   'pdf',   'pdf'),
    ]
    # Database & Sync tab — current paths
    from pathlib import Path
    import os
    BASE_DIR = Path(django_settings.BASE_DIR)
    db_path   = str(django_settings.DATABASES['default']['NAME'])
    media_path = str(django_settings.MEDIA_ROOT)
    # Read db_path.txt if exists
    txt_file = BASE_DIR / 'db_path.txt'
    db_path_config_line1 = ''
    db_path_config_line2 = ''
    if txt_file.exists():
        lines = txt_file.read_text(encoding='utf-8').splitlines()
        db_path_config_line1 = lines[0].strip() if len(lines) > 0 else ''
        db_path_config_line2 = lines[1].strip() if len(lines) > 1 else ''
    return render(request, 'lab/lab_settings.html', {
        'settings': settings,
        'role': get_role(request),
        'sig_fields': sig_fields,
        'margins_groups': margins_groups,
        'margins_types': margins_types,
        'db_path': db_path,
        'media_path': media_path,
        'db_path_config_line1': db_path_config_line1,
        'db_path_config_line2': db_path_config_line2,
    })

@login_required
@admin_only
def lab_settings_save(request):
    from .models import LabSettings
    if request.method == 'POST':
        s = LabSettings.get()
        s.lab_name  = request.POST.get('lab_name', s.lab_name)
        s.tagline   = request.POST.get('tagline', s.tagline)
        s.unit_text = request.POST.get('unit_text', s.unit_text)
        s.nabl_text = request.POST.get('nabl_text', s.nabl_text)
        s.email     = request.POST.get('email', s.email)
        s.phone     = request.POST.get('phone', s.phone)
        s.address   = request.POST.get('address', s.address)
        # Pro Suite password
        new_pro_pw = request.POST.get('pro_suite_password', '').strip()
        if new_pro_pw:
            s.pro_suite_password = new_pro_pw
        s.pdf_footer_text   = request.POST.get('pdf_footer_text', s.pdf_footer_text)
        s.show_timing_bar   = bool(request.POST.get('show_timing_bar'))
        s.timing_text       = request.POST.get('timing_text', s.timing_text)
        s.facilities_text   = request.POST.get('facilities_text', s.facilities_text)
        # -- SMS / WhatsApp settings --
        s.sms_provider        = request.POST.get('sms_provider', s.sms_provider)
        s.msg91_auth_key      = request.POST.get('msg91_auth_key', s.msg91_auth_key)
        s.msg91_sender_id     = request.POST.get('msg91_sender_id', s.msg91_sender_id)
        s.msg91_template_id   = request.POST.get('msg91_template_id', s.msg91_template_id)
        s.twilio_account_sid  = request.POST.get('twilio_account_sid', s.twilio_account_sid)
        s.twilio_auth_token   = request.POST.get('twilio_auth_token', s.twilio_auth_token)
        s.twilio_from_number  = request.POST.get('twilio_from_number', s.twilio_from_number)
        s.whatsapp_enabled    = bool(request.POST.get('whatsapp_enabled'))
        s.whatsapp_token      = request.POST.get('whatsapp_token', s.whatsapp_token)
        s.whatsapp_phone_id   = request.POST.get('whatsapp_phone_id', s.whatsapp_phone_id)
        # -- Razorpay settings --
        s.razorpay_key_id         = request.POST.get('razorpay_key_id', s.razorpay_key_id)
        s.razorpay_key_secret     = request.POST.get('razorpay_key_secret', s.razorpay_key_secret)
        s.razorpay_webhook_secret = request.POST.get('razorpay_webhook_secret', s.razorpay_webhook_secret)
        # -- HIS / HL7 settings --
        s.his_endpoint_url = request.POST.get('his_endpoint_url', s.his_endpoint_url)
        s.his_auth_token   = request.POST.get('his_auth_token', s.his_auth_token)
        # -- AI settings --
        s.ai_auto_interpret = bool(request.POST.get('ai_auto_interpret'))
        s.openai_api_key    = request.POST.get('openai_api_key', s.openai_api_key)
        # -- Landing page settings --
        s.landing_patients = request.POST.get('landing_patients', s.landing_patients)
        s.landing_tests    = request.POST.get('landing_tests', s.landing_tests)
        s.landing_years    = request.POST.get('landing_years', s.landing_years)
        s.about_text       = request.POST.get('about_text', s.about_text)
        s.services_text    = request.POST.get('services_text', s.services_text)
        s.feedback_email   = request.POST.get('feedback_email', s.feedback_email)
        # Margin settings
        def _int(key, default):
            try: return max(0, min(500, int(request.POST.get(key, default))))
            except: return default
        s.print_single_margin_top    = _int('print_single_margin_top',    s.print_single_margin_top)
        s.print_single_margin_bottom = _int('print_single_margin_bottom', s.print_single_margin_bottom)
        s.print_single_margin_left   = _int('print_single_margin_left',   s.print_single_margin_left)
        s.print_single_margin_right  = _int('print_single_margin_right',  s.print_single_margin_right)
        s.pdf_single_margin_top      = _int('pdf_single_margin_top',      s.pdf_single_margin_top)
        s.pdf_single_margin_bottom   = _int('pdf_single_margin_bottom',   s.pdf_single_margin_bottom)
        s.pdf_single_margin_left     = _int('pdf_single_margin_left',     s.pdf_single_margin_left)
        s.pdf_single_margin_right    = _int('pdf_single_margin_right',    s.pdf_single_margin_right)
        s.print_bulk_margin_top      = _int('print_bulk_margin_top',      s.print_bulk_margin_top)
        s.print_bulk_margin_bottom   = _int('print_bulk_margin_bottom',   s.print_bulk_margin_bottom)
        s.print_bulk_margin_left     = _int('print_bulk_margin_left',     s.print_bulk_margin_left)
        s.print_bulk_margin_right    = _int('print_bulk_margin_right',    s.print_bulk_margin_right)
        s.pdf_bulk_margin_top        = _int('pdf_bulk_margin_top',        s.pdf_bulk_margin_top)
        s.pdf_bulk_margin_bottom     = _int('pdf_bulk_margin_bottom',     s.pdf_bulk_margin_bottom)
        s.pdf_bulk_margin_left       = _int('pdf_bulk_margin_left',       s.pdf_bulk_margin_left)
        s.pdf_bulk_margin_right      = _int('pdf_bulk_margin_right',      s.pdf_bulk_margin_right)
        s.print_bill_margin_top      = _int('print_bill_margin_top',      s.print_bill_margin_top)
        s.print_bill_margin_bottom   = _int('print_bill_margin_bottom',   s.print_bill_margin_bottom)
        s.print_bill_margin_left     = _int('print_bill_margin_left',     s.print_bill_margin_left)
        s.print_bill_margin_right    = _int('print_bill_margin_right',    s.print_bill_margin_right)
        s.pdf_bill_margin_top        = _int('pdf_bill_margin_top',        s.pdf_bill_margin_top)
        s.pdf_bill_margin_bottom     = _int('pdf_bill_margin_bottom',     s.pdf_bill_margin_bottom)
        s.pdf_bill_margin_left       = _int('pdf_bill_margin_left',       s.pdf_bill_margin_left)
        s.pdf_bill_margin_right      = _int('pdf_bill_margin_right',      s.pdf_bill_margin_right)
        # Signer names & qualifications
        for i in range(1, 5):
            s.__dict__[f'signer{i}_name'] = request.POST.get(f'signer{i}_name', getattr(s, f'signer{i}_name'))
            s.__dict__[f'signer{i}_qual'] = request.POST.get(f'signer{i}_qual', getattr(s, f'signer{i}_qual'))
        s.signer_image_height = _int('signer_image_height', s.signer_image_height)
        s.report_font_size    = max(8, min(20, _int('report_font_size', s.report_font_size)))
        # Handle image uploads
        for field in ['logo_image','letterhead_image','pdf_header_image','pdf_footer_image','footer_image',
                      'signature_ansari','signature_saleem','signature_kumar','signature_maurya']:
            if request.FILES.get(field):
                setattr(s, field, request.FILES[field])
            elif request.POST.get(f'clear_{field}'):
                setattr(s, field, None)
        s.save()
        # Save db_path.txt — only if Pro Suite is unlocked
        from pathlib import Path
        from django.conf import settings as django_settings
        from django.db import connections
        BASE_DIR = Path(django_settings.BASE_DIR)
        if request.session.get('pro_suite_unlocked'):
            line1 = request.POST.get('db_path_line1', '').strip()
            line2 = request.POST.get('db_path_line2', '').strip()
            txt_file = BASE_DIR / 'db_path.txt'
            if line1 or line2:
                txt_file.write_text(f"{line1}\n{line2}\n", encoding='utf-8')
            elif txt_file.exists() and not line1 and not line2:
                txt_file.unlink(missing_ok=True)
                line1 = ''
                line2 = ''
            # ── Live switch: apply new DB path immediately without server restart ──
            new_db = Path(line1) if line1 else BASE_DIR / 'db.sqlite3'
            new_media = Path(line2) if line2 else BASE_DIR / 'media'
            # Close existing connection so Django re-opens with new path
            connections['default'].close()
            # Patch Django settings in-process
            django_settings.DATABASES['default']['NAME'] = new_db
            django_settings.MEDIA_ROOT = new_media
            # Run migrations on new DB so it's ready immediately
            from django.core.management import call_command
            import io
            try:
                call_command('migrate', '--run-syncdb', verbosity=0, stdout=io.StringIO())
            except Exception:
                pass
            messages.success(request, f"✅ Settings saved! Database switched to: {new_db}")
        else:
            messages.success(request, "Lab settings saved successfully.")
    return redirect('lab_settings')


# --- Test Note Save -----------------------------------------------------------

@login_required
@admin_only
def test_note_save(request, pk):
    from .models import TestNote
    test = get_object_or_404(Test, pk=pk)
    if request.method == 'POST':
        note_text = request.POST.get('note_text', '').strip()
        if note_text:
            TestNote.objects.update_or_create(test=test, defaults={'note_text': note_text})
            messages.success(request, f"Note saved for {test.name}.")
        else:
            TestNote.objects.filter(test=test).delete()
            messages.success(request, "Note removed.")
    return redirect('test_params', pk=pk)


# --- Bulk Report PDF/Print ----------------------------------------------------

@login_required
def bulk_report_pdf(request):
    """Generate combined PDF with letterhead for selected reports. Used for WhatsApp/email sharing."""
    from .models import LabSettings
    ids = request.GET.getlist('ids')
    if not ids:
        messages.error(request, "No reports selected.")
        return redirect('reports')
    reports_qs = Report.objects.filter(pk__in=ids).select_related(
        'booking__patient','booking__ref_doctor','booking','test'
    ).prefetch_related('results')
    # Role check for patients
    role = get_role(request)
    if role == 'patient':
        try:
            pt = request.user.patient_profile
            reports_qs = reports_qs.filter(booking__patient=pt, is_finalized=True)
        except Exception:
            return HttpResponse("Access denied", status=403)
    lab = LabSettings.get()
    reports_with_qr = []
    for rpt in reports_qs:
        qr_url = request.build_absolute_uri(f'/report/{rpt.pk}/view/?qr=1')
        reports_with_qr.append({'report': rpt, 'qr_b64': generate_qr_base64(qr_url)})
    return render(request, 'lab/bulk_report_pdf.html', {
        'reports': reports_qs, 'reports_with_qr': reports_with_qr, 'lab': lab, 'letterhead': True
    })

@login_required
@doc_access
def bulk_report_print(request):
    """Bulk Print - uses bulk print margins from Lab Settings."""""
    from .models import LabSettings
    ids = request.GET.getlist('ids')
    if not ids:
        messages.error(request, "No reports selected.")
        return redirect('reports')
    reports_qs = Report.objects.filter(pk__in=ids).select_related(
        'booking__patient','booking__ref_doctor','booking','test'
    ).prefetch_related('results')
    lab = LabSettings.get()
    reports_with_qr = []
    for rpt in reports_qs:
        qr_url = request.build_absolute_uri(f'/report/{rpt.pk}/view/')
        reports_with_qr.append({'report': rpt, 'qr_b64': generate_qr_base64(qr_url)})
    return render(request, 'lab/bulk_report_print.html', {
        'reports': reports_qs, 'reports_with_qr': reports_with_qr, 'lab': lab, 'letterhead': False
    })


# --- Advanced Search ---------------------------------------------------------

@login_required
@doc_access
def advanced_search(request):
    q         = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    search_in = request.GET.get('search_in', 'all')

    patients = Patient.objects.none()
    reports  = Report.objects.none()
    bookings = Booking.objects.none()

    if q or date_from or date_to:
        # Patient search
        pt_qs = Patient.objects.all()
        if q:
            pt_qs = pt_qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(mobile__icontains=q)     | Q(patient_id__icontains=q) |
                Q(custom_display_id__icontains=q)
            )
        if date_from:
            pt_qs = pt_qs.filter(registered_at__date__gte=date_from)
        if date_to:
            pt_qs = pt_qs.filter(registered_at__date__lte=date_to)
        patients = pt_qs[:50]

        # Report search
        rpt_qs = Report.objects.select_related('booking__patient','test').all()
        if q:
            rpt_qs = rpt_qs.filter(
                Q(report_id__icontains=q) |
                Q(booking__patient__first_name__icontains=q) |
                Q(booking__patient__last_name__icontains=q)  |
                Q(booking__patient__mobile__icontains=q)     |
                Q(test__name__icontains=q)
            )
        if date_from:
            rpt_qs = rpt_qs.filter(report_date__gte=date_from)
        if date_to:
            rpt_qs = rpt_qs.filter(report_date__lte=date_to)
        reports = rpt_qs[:50]

    # Test search
    tests = []
    if q:
        from .models import Test
        tests = list(Test.objects.filter(active=True, name__icontains=q).order_by('category','name')[:30])

    return render(request, 'lab/advanced_search.html', {
        'patients': patients, 'reports': reports, 'tests': tests,
        'q': q, 'date_from': date_from, 'date_to': date_to,
        'role': get_role(request),
    })


# --- Chatbot ------------------------------------------------------------------

@login_required
def chatbot(request):
    return render(request, 'lab/chatbot.html')


# --- Payments & Billing ------------------------------------------------------
# FEATURE: MULTI-BRANCH
# --- Payments & Billing ------------------------------------------------------

@login_required
@admin_only
def branches_list(request):
    from .models import Branch
    branches = Branch.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        if name:
            Branch.objects.create(
                name=name,
                address=request.POST.get('address',''),
                phone=request.POST.get('phone',''),
                email=request.POST.get('email',''),
            )
            messages.success(request, f"Branch '{name}' created.")
        return redirect('branches')
    return render(request, 'lab/branches.html', {'branches': branches, 'role': get_role(request)})


@login_required
@admin_only
def branch_delete(request, pk):
    from .models import Branch
    get_object_or_404(Branch, pk=pk).delete()
    messages.success(request, "Branch deleted.")
    return redirect('branches')


# --- Insurance --------------------------------------------------------------
# FEATURE: SMS/WHATSAPP NOTIFICATIONS
# --- Insurance --------------------------------------------------------------

@login_required
@admin_only
def notifications_list(request):
    from .models import NotificationLog
    logs = NotificationLog.objects.select_related('patient','related_report').order_by('-sent_at')[:200]
    return render(request, 'lab/notifications.html', {'logs': logs, 'role': get_role(request)})


@login_required
@staff_access
def send_report_sms(request, report_pk):
    """Manually trigger SMS/WhatsApp for a report."""
    from .notifications import send_report_ready_sms
    report = get_object_or_404(__import__('lab.models', fromlist=['Report']).Report, pk=report_pk)
    success = send_report_ready_sms(report)
    if success:
        messages.success(request, "SMS/WhatsApp sent successfully.")
    else:
        messages.warning(request, "SMS could not be sent. Please configure the provider in Lab Settings.")
    return redirect('report_view', report_pk=report_pk)


# --- Notifications ----------------------------------------------------------
# FEATURE: ONLINE PAYMENT (Razorpay)
# --- Notifications ----------------------------------------------------------

@login_required
@staff_access
def payment_create_order(request, booking_pk):
    """Create Razorpay order and return JSON for checkout."""
    from .payments import create_payment_order
    from .models import LabSettings
    booking = get_object_or_404(__import__('lab.models', fromlist=['Booking']).Booking, pk=booking_pk)
    if booking.due <= 0:
        return JsonResponse({'error': 'No due amount.'}, status=400)
    try:
        po, rz_order = create_payment_order(booking)
        s = LabSettings.get()
        return JsonResponse({
            'order_id': rz_order['id'],
            'amount': rz_order['amount'],
            'currency': rz_order['currency'],
            'key_id': getattr(s, 'razorpay_key_id', ''),
            'patient_name': booking.patient.full_name,
            'patient_email': booking.patient.email,
            'patient_mobile': booking.patient.mobile,
            'receipt': booking.receipt_id,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@staff_access
def payment_verify(request):
    """Verify Razorpay payment after checkout success."""
    from .payments import handle_payment_success
    if request.method == 'POST':
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        success = handle_payment_success(
            data.get('razorpay_order_id',''),
            data.get('razorpay_payment_id',''),
            data.get('razorpay_signature',''),
        )
        if success:
            messages.success(request, "Payment successful! Booking updated.")
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Signature verification failed'}, status=400)
    return JsonResponse({'error': 'POST only'}, status=405)


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def payment_webhook(request):
    """Razorpay webhook endpoint (CSRF exempt). Verify and process events."""
    from .payments import handle_payment_success
    import hashlib, hmac
    from .models import LabSettings
    if request.method != 'POST':
        return HttpResponse(status=405)
    s = LabSettings.get()
    webhook_secret = getattr(s, 'razorpay_webhook_secret', '').encode()
    if webhook_secret:
        sig = request.headers.get('X-Razorpay-Signature', '')
        expected = hmac.new(webhook_secret, request.body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return HttpResponse(status=403)
    try:
        payload = json.loads(request.body)
        event   = payload.get('event', '')
        if event == 'payment.captured':
            payment = payload['payload']['payment']['entity']
            # For webhook, we verify differently -- just update status
            from .models import PaymentOrder
            from django.utils import timezone
            po = PaymentOrder.objects.filter(razorpay_order_id=payment.get('order_id','')).first()
            if po and po.status != 'paid':
                po.razorpay_payment_id = payment.get('id','')
                po.status = 'paid'
                po.paid_at = timezone.now()
                po.save()
                booking = po.booking
                booking.paid = booking.paid + po.amount
                booking.due  = max(0, booking.total - booking.paid)
                booking.save()
    except Exception as e:
        pass
    return HttpResponse(status=200)


@login_required
@admin_only
def payments_list(request):
    """List all payment orders."""
    from .models import PaymentOrder
    orders = PaymentOrder.objects.select_related('booking__patient').order_by('-created_at')[:200]
    return render(request, 'lab/payments.html', {'orders': orders, 'role': get_role(request)})


# --- Branches ---------------------------------------------------------------
# FEATURE: INSURANCE CLAIMS
# --- Branches ---------------------------------------------------------------

@login_required
@staff_access
def insurance_claims_list(request):
    from .models import InsuranceClaim
    claims = InsuranceClaim.objects.select_related('booking__patient','insurance_co').order_by('-created_at')
    return render(request, 'lab/insurance_claims.html', {'claims': claims, 'role': get_role(request)})


@login_required
@staff_access
def insurance_claim_new(request, booking_pk):
    from .models import InsuranceClaim, InsuranceCompany, Booking
    booking = get_object_or_404(Booking, pk=booking_pk)
    companies = InsuranceCompany.objects.filter(is_active=True)
    if request.method == 'POST':
        ic_pk = request.POST.get('insurance_co')
        claim = InsuranceClaim.objects.create(
            booking=booking,
            insurance_co=InsuranceCompany.objects.filter(pk=ic_pk).first() if ic_pk else None,
            policy_number=request.POST.get('policy_number',''),
            member_id=request.POST.get('member_id',''),
            claim_amount=request.POST.get('claim_amount', booking.total),
            status='draft',
            created_by=request.user,
        )
        messages.success(request, f"Insurance claim {claim.claim_no} created.")
        return redirect('insurance_claim_detail', pk=claim.pk)
    return render(request, 'lab/insurance_claim_new.html', {
        'booking': booking, 'companies': companies, 'role': get_role(request)
    })


@login_required
@staff_access
def insurance_claim_detail(request, pk):
    from .models import InsuranceClaim
    from django.utils import timezone
    claim = get_object_or_404(InsuranceClaim, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action','')
        if action == 'submit':
            claim.status = 'submitted'
            claim.submitted_at = timezone.now()
            claim.save()
            messages.success(request, "Claim submitted.")
        elif action == 'approve':
            claim.status = 'approved'
            claim.approved_amount = request.POST.get('approved_amount', claim.claim_amount)
            claim.save()
            messages.success(request, "Claim approved.")
        elif action == 'reject':
            claim.status = 'rejected'
            claim.remarks = request.POST.get('remarks', '')
            claim.save()
            messages.warning(request, "Claim rejected.")
        elif action == 'settle':
            claim.status = 'settled'
            claim.settled_at = timezone.now()
            claim.save()
            messages.success(request, "Claim settled.")
        elif action == 'update':
            claim.policy_number = request.POST.get('policy_number', claim.policy_number)
            claim.member_id     = request.POST.get('member_id', claim.member_id)
            claim.remarks       = request.POST.get('remarks', claim.remarks)
            claim.save()
            messages.success(request, "Claim updated.")
        return redirect('insurance_claim_detail', pk=pk)
    return render(request, 'lab/insurance_claim_detail.html', {'claim': claim, 'role': get_role(request)})


@login_required
@admin_only
def insurance_companies_list(request):
    from .models import InsuranceCompany
    companies = InsuranceCompany.objects.all()
    if request.method == 'POST':
        InsuranceCompany.objects.create(
            name=request.POST.get('name',''),
            tpa_name=request.POST.get('tpa_name',''),
            contact=request.POST.get('contact',''),
            email=request.POST.get('email',''),
        )
        messages.success(request, "Insurance company added.")
        return redirect('insurance_companies')
    return render(request, 'lab/insurance_companies.html', {'companies': companies, 'role': get_role(request)})


# --- QC Log -----------------------------------------------------------------
# FEATURE: HL7/FHIR
# --- QC Log -----------------------------------------------------------------

@login_required
@admin_only
def hl7_fhir_log(request):
    from .models import HL7FHIRLog
    logs = HL7FHIRLog.objects.select_related('patient','report').order_by('-created_at')[:200]
    return render(request, 'lab/hl7_fhir_log.html', {'logs': logs, 'role': get_role(request)})


@login_required
@staff_access
def fhir_export_report(request, report_pk):
    """Export a report as FHIR DiagnosticReport JSON."""
    from .hl7_fhir import generate_fhir_diagnostic_report
    from .models import Report
    report = get_object_or_404(Report, pk=report_pk)
    bundle = generate_fhir_diagnostic_report(report)
    resp = HttpResponse(
        json.dumps(bundle, indent=2, default=str),
        content_type='application/fhir+json'
    )
    resp['Content-Disposition'] = f'attachment; filename="FHIR_{report.report_id}.json"'
    return resp


@login_required
@staff_access
def hl7_send_report(request, report_pk):
    """Send report to HIS via HL7 ORU^R01."""
    from .hl7_fhir import send_to_his
    from .models import Report
    report = get_object_or_404(Report, pk=report_pk)
    result = send_to_his(report)
    if result['success']:
        messages.success(request, f"HL7 message sent to HIS. Status: {result['status_code']}")
    else:
        messages.error(request, f"HL7 send failed: {result['response']}")
    return redirect('report_view', report_pk=report_pk)


# --- Critical Alerts --------------------------------------------------------
# FEATURE: MACHINE ANALYSER INTERFACE
# --- Critical Alerts --------------------------------------------------------

@login_required
@admin_only
def analyser_list(request):
    from .models import AnalyserInterface, AnalyserResult
    analysers = AnalyserInterface.objects.all()
    pending   = AnalyserResult.objects.filter(status='pending').select_related('analyser').order_by('-received_at')[:50]
    return render(request, 'lab/analyser.html', {
        'analysers': analysers, 'pending_results': pending, 'role': get_role(request)
    })


@login_required
@admin_only
def analyser_add(request):
    from .models import AnalyserInterface
    if request.method == 'POST':
        AnalyserInterface.objects.create(
            name=request.POST.get('name',''),
            protocol=request.POST.get('protocol','ASTM'),
            host=request.POST.get('host',''),
            port=request.POST.get('port') or None,
            test_mapping=request.POST.get('test_mapping','{}'),
        )
        messages.success(request, "Analyser interface added.")
    return redirect('analyser_list')


@login_required
@staff_access
def analyser_import_result(request, result_pk):
    """Manually trigger import of an AnalyserResult into a report."""
    from .analyser import import_analyser_result
    result = import_analyser_result(result_pk)
    if result['success']:
        messages.success(request, f"Imported {result['imported']} parameters into {result['report_id']}.")
    else:
        messages.error(request, f"Import failed: {'; '.join(result['errors'])}")
    return redirect('analyser_list')


@login_required
@staff_access
def analyser_upload_csv(request):
    """Upload CSV result file from analyser."""
    from .analyser import parse_csv_result
    from .models import AnalyserResult
    if request.method == 'POST' and request.FILES.get('csv_file'):
        f = request.FILES['csv_file']
        content = f.read().decode('utf-8', errors='replace')
        parsed  = parse_csv_result(content)
        ar = AnalyserResult.objects.create(
            sample_id=parsed.get('sample_id','UNKNOWN'),
            raw_data=content,
            parsed_json=json.dumps(parsed),
            status='pending',
        )
        from .analyser import import_analyser_result
        result = import_analyser_result(ar.pk)
        if result['success']:
            messages.success(request, f"CSV imported: {result['imported']} params into {result['report_id']}.")
        else:
            messages.warning(request, f"CSV uploaded but import incomplete: {'; '.join(result['errors'])}")
    return redirect('analyser_list')


# --- Home Collections -------------------------------------------------------
# FEATURE: AI INTERPRETATION
# --- Home Collections -------------------------------------------------------

@login_required
@doc_access
def ai_interpretation(request, report_pk):
    from .models import Report
    from .ai_interpretation import generate_interpretation
    report = get_object_or_404(Report, pk=report_pk)
    ai = generate_interpretation(report)
    return render(request, 'lab/ai_interpretation.html', {
        'report': report, 'ai': ai, 'role': get_role(request)
    })


@login_required
@staff_access
def ai_interpretation_approve(request, report_pk):
    from .models import Report, AIInterpretation
    from django.utils import timezone
    report = get_object_or_404(Report, pk=report_pk)
    try:
        ai = report.ai_interpretation
        ai.status = 'approved'
        ai.reviewed_by = request.user
        ai.reviewed_at = timezone.now()
        ai.save()
        messages.success(request, "AI interpretation approved.")
    except Exception:
        messages.error(request, "Interpretation not found.")
    return redirect('ai_interpretation', report_pk=report_pk)


# --- Revenue Report ---------------------------------------------------------
# FEATURE: MOBILE APP -- Push notifications / device token registration
# --- Revenue Report ---------------------------------------------------------

@csrf_exempt
def mobile_register_token(request):
    """Mobile app calls this to register FCM/APNs push token."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        token    = data.get('token', '')
        platform = data.get('platform', 'android')
        user_pk  = data.get('user_pk')
        if not token or not user_pk:
            return JsonResponse({'error': 'token and user_pk required'}, status=400)
        from django.contrib.auth.models import User
        from .models import MobileDeviceToken
        user = User.objects.get(pk=user_pk)
        MobileDeviceToken.objects.update_or_create(
            user=user, token=token,
            defaults={'platform': platform, 'is_active': True}
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def mobile_api_reports(request):
    """REST API endpoint for mobile app. Returns patient reports as JSON."""
    try:
        pt = request.user.patient_profile
    except Exception:
        return JsonResponse({'error': 'Patient profile not found'}, status=404)
    from .models import Report
    reports = Report.objects.filter(
        booking__patient=pt, is_finalized=True
    ).select_related('test','booking').order_by('-report_date')[:50]
    data = [{
        'report_id':    r.report_id,
        'test':         r.test.display_name,
        'date':         str(r.report_date),
        'finalized':    r.is_finalized,
        'booking_id':   r.booking.receipt_id,
    } for r in reports]
    return JsonResponse({'reports': data})


# --- Inventory --------------------------------------------------------------
# TEST PROFILES (PANELS)
# --- Inventory --------------------------------------------------------------

@login_required
def test_profiles(request):
    from .models import TestProfile, Test
    profiles = TestProfile.objects.prefetch_related('tests').all()
    all_tests = Test.objects.filter(active=True).order_by('category','name')
    quick_profiles = [
        'Fever Profile','Liver Function Test (LFT)','Kidney Function Test (KFT)',
        'Lipid Profile','Diabetes Profile','Thyroid Profile',
        'Complete Hemogram','Cardiac Profile','Antenatal Profile','Arthritis Profile',
    ]
    return render(request, 'lab/test_profiles.html', {
        'profiles': profiles, 'all_tests': all_tests,
        'role': get_role(request), 'user_role': get_role(request),
        'quick_profiles': quick_profiles,
    })

@login_required
@admin_only
def test_profile_add(request):
    from .models import TestProfile, Test
    if request.method == 'POST':
        p = TestProfile.objects.create(
            name=request.POST.get('name','').strip(),
            short_code=request.POST.get('short_code','').strip(),
            description=request.POST.get('description','').strip(),
            price=request.POST.get('price',0) or 0,
            sort_order=request.POST.get('sort_order',0) or 0,
        )
        test_ids = request.POST.getlist('tests')
        if test_ids:
            p.tests.set(Test.objects.filter(pk__in=test_ids))
        messages.success(request, f"Profile '{p.name}' ({p.profile_code}) created.")
    return redirect('test_profiles')

@login_required
@admin_only
def test_profile_edit(request, pk):
    from .models import TestProfile, Test
    p = get_object_or_404(TestProfile, pk=pk)
    if request.method == 'POST':
        p.name        = request.POST.get('name', p.name).strip()
        p.short_code  = request.POST.get('short_code', p.short_code).strip()
        p.description = request.POST.get('description', p.description).strip()
        p.price       = request.POST.get('price', p.price) or 0
        p.sort_order  = request.POST.get('sort_order', p.sort_order) or 0
        p.is_active   = bool(request.POST.get('is_active'))
        p.save()
        test_ids = request.POST.getlist('tests')
        p.tests.set(Test.objects.filter(pk__in=test_ids))
        messages.success(request, f"Profile '{p.name}' updated.")
        return redirect('test_profiles')
    all_tests = Test.objects.filter(active=True).order_by('category','name')
    return render(request, 'lab/test_profile_edit.html', {
        'profile': p, 'all_tests': all_tests, 'role': get_role(request), 'user_role': get_role(request)
    })

@login_required
@admin_only
def test_profile_delete(request, pk):
    from .models import TestProfile
    get_object_or_404(TestProfile, pk=pk).delete()
    messages.success(request, "Profile deleted.")
    return redirect('test_profiles')

@login_required
def api_profile_tests(request, pk):
    """AJAX: return tests + total price for a profile (for booking form)."""
    from .models import TestProfile
    p = get_object_or_404(TestProfile, pk=pk)
    tests = [{'id': t.pk, 'name': t.name, 'price': str(t.price)} for t in p.tests.filter(active=True)]
    return JsonResponse({'tests': tests, 'total': str(p.price), 'name': p.name})


# --- Doctor Commissions -----------------------------------------------------
# HOME COLLECTION
# --- Doctor Commissions -----------------------------------------------------

@login_required
@staff_access
def home_collections(request):
    from .models import HomeCollection
    collections = HomeCollection.objects.select_related('booking__patient','phlebotomist').order_by('-scheduled_date','-scheduled_time')
    return render(request, 'lab/home_collections.html', {'collections': collections, 'role': get_role(request)})

@login_required
@staff_access
def home_collection_add(request, booking_pk):
    from .models import HomeCollection, Booking
    booking = get_object_or_404(Booking, pk=booking_pk)
    if request.method == 'POST':
        HomeCollection.objects.update_or_create(booking=booking, defaults={
            'address': request.POST.get('address',''),
            'scheduled_date': request.POST.get('scheduled_date'),
            'scheduled_time': request.POST.get('scheduled_time'),
            'collection_fee': request.POST.get('collection_fee',0) or 0,
            'remarks': request.POST.get('remarks',''),
        })
        messages.success(request, "Home collection scheduled.")
        return redirect('booking_detail', pk=booking_pk)
    return render(request, 'lab/home_collection_form.html', {'booking': booking, 'role': get_role(request)})


# --- Expenditures -----------------------------------------------------------
# DOCTOR COMMISSION
# --- Expenditures -----------------------------------------------------------

@login_required
@admin_only
def doctor_commissions(request):
    from .models import DoctorCommission, Doctor
    commissions = DoctorCommission.objects.select_related('doctor').prefetch_related('bookings').order_by('-month')
    doctors = Doctor.objects.all()
    return render(request, 'lab/doctor_commissions.html', {
        'commissions': commissions, 'doctors': doctors, 'role': get_role(request)
    })

@login_required
@admin_only
def doctor_commission_generate(request):
    """Generate monthly commission for a doctor."""
    from .models import DoctorCommission, Doctor, Booking
    import datetime
    if request.method == 'POST':
        doc_pk  = request.POST.get('doctor')
        month_s = request.POST.get('month')  # YYYY-MM
        pct     = float(request.POST.get('commission_pct', 0) or 0)
        try:
            doctor = Doctor.objects.get(pk=doc_pk)
            month_date = datetime.date.fromisoformat(month_s + '-01')
            bookings = Booking.objects.filter(
                ref_doctor=doctor,
                booking_date__year=month_date.year,
                booking_date__month=month_date.month
            )
            total = sum(b.total for b in bookings)
            # Convert to Decimal to avoid Decimal*float TypeError
            from decimal import Decimal as D
            comm_amt = D(str(total)) * D(str(pct)) / D('100')
            comm, _ = DoctorCommission.objects.update_or_create(
                doctor=doctor, month=month_date,
                defaults={'total_billing': total, 'commission_pct': pct, 'commission_amt': comm_amt}
            )
            comm.bookings.set(bookings)
            messages.success(request, f"Commission generated: Dr. {doctor.name} -- ₹{comm_amt:.0f}")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('doctor_commissions')


@login_required
@admin_only
def commission_mark_paid(request, pk):
    """Mark a commission as paid."""
    from .models import DoctorCommission
    import datetime
    comm = get_object_or_404(DoctorCommission, pk=pk)
    comm.status = 'paid'
    comm.paid_on = datetime.date.today()
    comm.save()
    messages.success(request, f"Commission for Dr. {comm.doctor.name} marked as Paid.")
    return redirect('doctor_commissions')


@login_required
@admin_only
def commission_edit(request, pk):
    """Edit commission % and remarks."""
    from .models import DoctorCommission
    comm = get_object_or_404(DoctorCommission, pk=pk)
    if request.method == 'POST':
        pct = float(request.POST.get('commission_pct', comm.commission_pct) or 0)
        comm.commission_pct = pct
        from decimal import Decimal as D
        comm.commission_amt = D(str(comm.total_billing)) * D(str(pct)) / D('100')
        comm.remarks = request.POST.get('remarks', '')
        comm.status = request.POST.get('status', comm.status)
        comm.save()
        messages.success(request, "Commission updated.")
    return redirect('doctor_commissions')


@login_required
@admin_only
def commission_pdf(request, pk):
    """Generate printable PDF slip for a commission."""
    from .models import DoctorCommission, LabSettings
    comm = get_object_or_404(DoctorCommission.objects.select_related('doctor').prefetch_related('bookings'), pk=pk)
    lab = LabSettings.get()
    return render(request, 'lab/commission_pdf.html', {'comm': comm, 'lab': lab})


# EXPENDITURE
# --- HL7 / FHIR Export -----------------------------------------------------

@login_required
@staff_access
def expenditures(request):
    from .models import Expenditure, ExpenseCategory
    from django.db.models import Sum
    date_from = request.GET.get('from','')
    date_to   = request.GET.get('to','')
    qs = Expenditure.objects.select_related('category','added_by').order_by('-date')
    if date_from: qs = qs.filter(date__gte=date_from)
    if date_to:   qs = qs.filter(date__lte=date_to)
    total = qs.aggregate(t=Sum('amount'))['t'] or 0
    categories = ExpenseCategory.objects.all()
    if request.method == 'POST':
        cat_pk = request.POST.get('category')
        Expenditure.objects.create(
            date=request.POST.get('date'),
            description=request.POST.get('description',''),
            vendor=request.POST.get('vendor',''),
            amount=request.POST.get('amount',0),
            payment_mode=request.POST.get('payment_mode','Cash'),
            invoice_no=request.POST.get('invoice_no',''),
            category_id=cat_pk if cat_pk else None,
            added_by=request.user,
        )
        messages.success(request, "Expense added.")
        return redirect('expenditures')
    return render(request, 'lab/expenditures.html', {
        'expenses': qs[:200], 'total': total, 'categories': categories,
        'date_from': date_from, 'date_to': date_to, 'role': get_role(request)
    })


# --- AI Interpretation ------------------------------------------------------
# INVENTORY
# --- AI Interpretation ------------------------------------------------------

@login_required
@staff_access
def inventory(request):
    from .models import InventoryItem
    items = InventoryItem.objects.filter(is_active=True)
    low_stock = [i for i in items if i.is_low_stock]
    expired   = [i for i in items if i.is_expired]
    if request.method == 'POST':
        action = request.POST.get('action','add')
        if action == 'add':
            InventoryItem.objects.create(
                name=request.POST.get('name',''),
                category=request.POST.get('category',''),
                vendor=request.POST.get('vendor',''),
                unit=request.POST.get('unit','units'),
                current_stock=request.POST.get('current_stock',0) or 0,
                min_stock=request.POST.get('min_stock',0) or 0,
                unit_cost=request.POST.get('unit_cost',0) or 0,
                expiry_date=request.POST.get('expiry_date') or None,
            )
            messages.success(request, "Item added to inventory.")
        elif action == 'restock':
            item = get_object_or_404(InventoryItem, pk=request.POST.get('item_pk'))
            import datetime
            qty = float(request.POST.get('qty',0) or 0)
            item.current_stock += qty
            item.last_restocked = datetime.date.today()
            item.save()
            messages.success(request, f"{item.name} restocked by {qty} {item.unit}.")
        return redirect('inventory')
    return render(request, 'lab/inventory.html', {
        'items': items, 'low_stock': low_stock, 'expired': expired, 'role': get_role(request)
    })


# --- Landing Page -----------------------------------------------------------
# QC LOG
# --- Landing Page -----------------------------------------------------------

@login_required
@staff_access
def qc_log(request):
    from .models import QCLog
    import datetime
    logs = QCLog.objects.select_related('performed_by').order_by('-date','-created_at')[:200]
    if request.method == 'POST':
        QCLog.objects.create(
            date=request.POST.get('date', datetime.date.today()),
            instrument=request.POST.get('instrument',''),
            test_name=request.POST.get('test_name',''),
            control_level=request.POST.get('control_level',''),
            expected_value=request.POST.get('expected_value',''),
            obtained_value=request.POST.get('obtained_value',''),
            result=request.POST.get('result','pass'),
            remarks=request.POST.get('remarks',''),
            performed_by=request.user,
        )
        messages.success(request, "QC entry saved.")
        return redirect('qc_log')
    return render(request, 'lab/qc_log.html', {'logs': logs, 'role': get_role(request)})


# ===============================================================================
# CRITICAL VALUE ALERTS
# ===============================================================================

@login_required
@staff_access
def critical_alerts(request):
    from .models import CriticalValueAlert
    alerts = CriticalValueAlert.objects.select_related('report__booking__patient').filter(status='pending').order_by('-created_at')
    return render(request, 'lab/critical_alerts.html', {'alerts': alerts, 'role': get_role(request)})

@login_required
@staff_access
def critical_alert_resolve(request, pk):
    from .models import CriticalValueAlert
    from django.utils import timezone
    alert = get_object_or_404(CriticalValueAlert, pk=pk)
    if request.method == 'POST':
        alert.notified_to  = request.POST.get('notified_to', '')
        alert.notified_via = request.POST.get('notified_via', '')
        alert.status       = 'notified'
        alert.resolved_at  = timezone.now()
        alert.save()
        messages.success(request, "Critical alert marked as notified.")
    return redirect('critical_alerts')


# ===============================================================================
# REVENUE REPORT (Finance Dashboard)
# ===============================================================================

@login_required
@admin_only
def revenue_report(request):
    from .models import Booking, Expenditure
    from django.db.models import Sum
    import datetime

    today  = datetime.date.today()
    month_start = today.replace(day=1)

    ctx = {
        'role': get_role(request),
        'today': today,
        'revenue_today':   Booking.objects.filter(booking_date=today).aggregate(r=Sum('total'))['r'] or 0,
        'revenue_month':   Booking.objects.filter(booking_date__gte=month_start).aggregate(r=Sum('total'))['r'] or 0,
        'collected_today': Booking.objects.filter(booking_date=today).aggregate(r=Sum('paid'))['r'] or 0,
        'due_total':       Booking.objects.aggregate(r=Sum('due'))['r'] or 0,
        'expense_month':   Expenditure.objects.filter(date__gte=month_start).aggregate(r=Sum('amount'))['r'] or 0,
        'bookings_today':  Booking.objects.filter(booking_date=today).count(),
        'bookings_month':  Booking.objects.filter(booking_date__gte=month_start).count(),
        'recent_bookings': Booking.objects.filter(booking_date__gte=month_start).select_related('patient').order_by('-created_at')[:20],
    }
    return render(request, 'lab/revenue_report.html', ctx)


# ===============================================================================
# PRO SUITE PIN PROTECTION
# ===============================================================================

def pro_suite_lock(request):
    """Show PIN entry page for Pro Suite access."""
    error = ''
    if request.method == 'POST':
        from .models import LabSettings
        pin = request.POST.get('pin', '')
        lab = LabSettings.get()
        correct = lab.pro_suite_password or 'Jatin123'
        if pin == correct:
            request.session['pro_suite_unlocked'] = True
            next_url = request.POST.get('next', '/payments/')
            return redirect(next_url)
        error = 'Incorrect password. Please try again.'
    next_url = request.GET.get('next', '/payments/')
    return render(request, 'lab/pro_suite_lock.html', {'error': error, 'next': next_url})

def pro_suite_logout(request):
    """Lock Pro Suite again."""
    request.session.pop('pro_suite_unlocked', None)
    messages.success(request, 'Pro Suite locked.')
    return redirect('dashboard')


# ===============================================================================
# PUBLIC LANDING PAGE
# ===============================================================================

def landing_page(request):
    """Public-facing landing page for the lab."""
    from .models import LabSettings, Test
    lab = LabSettings.get()
    popular_tests = Test.objects.filter(active=True).order_by('?')[:6]
    feedback_sent = request.session.pop('feedback_sent', False)

    about_points = [
        {'icon': '🔬', 'title': 'State-of-the-art Instruments',     'desc': 'Advanced analysers from Sysmex, Mindray and other leading brands'},
        {'icon': 'Dr', 'title': 'Qualified Pathologists',           'desc': 'MD-qualified doctors and certified lab technicians on staff'},
        {'icon': '🏠', 'title': 'Home Sample Collection',            'desc': 'Trained phlebotomists collect samples from your home or office'},
        {'icon': '📱', 'title': 'Reports on WhatsApp / SMS',         'desc': 'Digital reports delivered directly to your phone'},
        {'icon': '💰', 'title': 'Affordable & Transparent Pricing',  'desc': 'No hidden charges. View our complete rate list online'},
        {'icon': '⚡', 'title': 'Fast & Accurate Results',           'desc': 'Most reports ready within 4-6 hours with high precision'},
    ]

    services_list = [
        {'name': 'Haematology',           'icon': '🩸', 'desc': 'CBC, ESR, peripheral smear'},
        {'name': 'Biochemistry',          'icon': '⚗️', 'desc': 'LFT, KFT, lipid, sugar'},
        {'name': 'Serology',              'icon': '🧪', 'desc': 'Typhoid, dengue, HIV, HBsAg'},
        {'name': 'Hormones',              'icon': '🔬', 'desc': 'Thyroid, fertility, cortisol'},
        {'name': 'Clinical Pathology',    'icon': '🧫', 'desc': 'Urine, stool, sputum analysis'},
        {'name': 'Histopathology',        'icon': '🔭', 'desc': 'Biopsy & tissue diagnosis'},
        {'name': 'Microbiology',          'icon': '🦠', 'desc': 'Culture & sensitivity tests'},
        {'name': 'Molecular Diagnostics', 'icon': '🧬', 'desc': 'PCR, RT-PCR testing'},
        {'name': 'Home Collection',       'icon': '🏠', 'desc': 'Sample pickup at your door'},
        {'name': 'Corporate Health',      'icon': '🏢', 'desc': 'Employee health checkups'},
        {'name': 'Cardiac Profile',       'icon': '❤️', 'desc': 'Troponin, CK-MB, BNP'},
    ]

    return render(request, 'lab/landing.html', {
        'lab': lab,
        'popular_tests': popular_tests,
        'feedback_sent': feedback_sent,
        'about_points': about_points,
        'services_list': services_list,
    })

def landing_feedback(request):
    """Handle feedback form submission from landing page."""
    if request.method == 'POST':
        # Store feedback in session to show success message
        request.session['feedback_sent'] = True
        # Simple: just log it (could save to DB / email)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Feedback from %s: %s", request.POST.get('fb_name'), request.POST.get('fb_message'))
        messages.success(request, 'Feedback received. Thank you!')
    return redirect('landing_page')
