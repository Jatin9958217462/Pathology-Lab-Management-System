"""
models.py -- PathLab v1.1
===============================================================================
Database models for the PathLab Laboratory Management System.

MODEL STRUCTURE:
  UserProfile          Extended user profile with role (admin/staff/doctor/patient)
  Doctor               Referring doctor with optional portal user link
  Test                 Lab test catalog (Haematology, Biochemistry, etc.)
  TestParameter        Individual parameters within a test (with ranges)
  TestNote             Per-test interpretation notes
  Patient              Patient demographic record
  Booking              Test booking linking patient + tests
  Report               Individual test report for a booking
  ReportResult         Single parameter result row in a report
  LabSettings          Singleton -- all lab branding, margins, images, SMS config
  DoctorCommission     Monthly commission tracking for referring doctors
  ExpenseCategory      Category for lab expenditures
  Expenditure          Individual expense record
  QCLog                Quality control log entry
  CriticalAlert        Critical result alert for urgent patient notification
  InsuranceCompany     Insurance provider master record
  InsuranceClaim       Insurance claim linked to a booking
  HomeCollection       Home sample collection request
  Branch               Lab branch / collection center

KEY DESIGN DECISIONS:
  - LabSettings uses a singleton pattern (get() class method)
  - All financial fields use DecimalField for precision
  - Images stored under media/branding/
  - Margin settings in pixels (converted to @page CSS rules in templates)

VERSION: 1.1
===============================================================================
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class UserProfile(models.Model):
    ROLES = [('admin','Administrator'),('staff','Lab Staff'),('doctor','Doctor'),('patient','Patient')]
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role        = models.CharField(max_length=20, choices=ROLES, default='patient')
    phone       = models.CharField(max_length=20, blank=True)
    unique_code = models.CharField(max_length=20, unique=True, blank=True, null=True,
                                   help_text='Auto-generated unique code for staff/doctor report access')

    def __str__(self): return f"{self.user.username} ({self.role})"
    def is_admin(self):  return self.role == 'admin'
    def is_staff_member(self): return self.role in ('admin','staff')
    def is_doctor_access(self): return self.role in ('admin','staff','doctor')

    def save(self, *args, **kwargs):
        if not self.unique_code and self.role in ('staff', 'doctor'):
            import random, string
            prefix = 'STF' if self.role == 'staff' else 'DOC'
            while True:
                code = prefix + '-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not UserProfile.objects.filter(unique_code=code).exists():
                    self.unique_code = code
                    break
        super().save(*args, **kwargs)


class Doctor(models.Model):
    doc_id        = models.CharField(max_length=20, unique=True, editable=False)
    name          = models.CharField(max_length=150)
    qualification = models.CharField(max_length=100, blank=True)
    specialization= models.CharField(max_length=100, blank=True)
    mobile        = models.CharField(max_length=20)
    email         = models.EmailField(blank=True)
    hospital      = models.CharField(max_length=200, blank=True)
    address       = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    linked_user   = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='doctor_profile',
        help_text='Portal user account linked to this doctor (for doctor panel access)'
    )

    def save(self, *args, **kwargs):
        if not self.doc_id:
            last = Doctor.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.doc_id = f"DOC-{n:03d}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name


class Test(models.Model):
    CATEGORIES = [
        ('Haematology','Haematology'),('Biochemistry','Biochemistry'),
        ('Serology','Serology'),('Clinical Pathology','Clinical Pathology'),
        ('Histopathology','Histopathology'),('Hormones','Hormones'),
    ]
    SAMPLES = [
        ('Blood (EDTA)','Blood (EDTA)'),('Blood (Plain)','Blood (Plain)'),
        ('Urine','Urine'),('Stool','Stool'),('Swab','Swab'),
        ('Sputum','Sputum'),('Semen','Semen'),('Tissue','Tissue'),
        ('Sodium Citrate','Sodium Citrate'),('Heparin','Heparin'),('Floride','Floride'),
    ]
    name     = models.CharField(max_length=200)
    full_name = models.CharField(max_length=300, blank=True, help_text='Optional full name (e.g. "Complete Blood Count" for CBC). If set, this shows on reports instead of short name.')
    category = models.CharField(max_length=50, choices=CATEGORIES, default='Haematology')
    price    = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sample   = models.CharField(max_length=30, choices=SAMPLES, default='Blood (Plain)')
    tat      = models.CharField(max_length=50, blank=True)
    active   = models.BooleanField(default=True)

    class Meta: ordering = ['category','name']
    def __str__(self): return f"{self.name} (₹{self.price})"

    @property
    def display_name(self):
        """Returns full_name if set, else name"""
        return self.full_name.strip() if self.full_name and self.full_name.strip() else self.name


class TestParameter(models.Model):
    """Defines reference parameters for each test (e.g. Hemoglobin: 11.5-16 g/dl)"""
    test        = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='parameters')
    param_name  = models.CharField(max_length=200)
    unit        = models.CharField(max_length=50, blank=True)
    lower_limit = models.FloatField(null=True, blank=True)
    upper_limit = models.FloatField(null=True, blank=True)
    is_text       = models.BooleanField(default=False)   # text result (e.g. Positive/Negative)
    sort_order    = models.PositiveIntegerField(default=0)
    test_method   = models.CharField(max_length=200, blank=True)
    default_value = models.CharField(max_length=100, blank=True, default='',
                                     help_text='Default value auto-filled when no reading entered')

    class Meta: ordering = ['sort_order']
    def __str__(self): return f"{self.test.name} -- {self.param_name}"

    @property
    def normal_range(self):
        if self.is_text: return "--"
        if self.lower_limit is not None and self.upper_limit is not None:
            return f"{self.lower_limit} - {self.upper_limit}"
        return "--"


class Patient(models.Model):
    HONORIFICS = [
        ('Mr.','Mr.'),('Mrs.','Mrs.'),('Ms.','Ms.'),('Miss','Miss'),
        ('Dr.','Dr.'),('Prof.','Prof.'),('Master','Master'),('Baby','Baby'),
        ('M/s','M/s'),
    ]
    AGE_UNITS = [('Years','Years'),('Months','Months'),('Days','Days')]
    GENDERS = [('Male','Male'),('Female','Female'),('Child (M)','Child (M)'),('Child (F)','Child (F)'),('Other','Other')]
    PRIORITIES = [('Normal','Normal'),('Urgent','Urgent'),('Emergency','Emergency')]
    BLOODS = [('','Unknown'),('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
              ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]

    patient_id  = models.CharField(max_length=20, unique=True, editable=False)
    honorific   = models.CharField(max_length=10, choices=[('Mr.','Mr.'),('Mrs.','Mrs.'),('Ms.','Ms.'),('Miss','Miss'),('Dr.','Dr.'),('Prof.','Prof.'),('Master','Master'),('Baby','Baby'),('M/s','M/s')], default='Mr.')
    age_unit    = models.CharField(max_length=10, choices=[('Years','Years'),('Months','Months'),('Days','Days')], default='Years')
    user        = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile')
    first_name  = models.CharField(max_length=100)
    last_name   = models.CharField(max_length=100, blank=True)
    age         = models.PositiveIntegerField()
    gender      = models.CharField(max_length=20, choices=GENDERS, default='Male')
    mobile      = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    address     = models.TextField(blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOODS, blank=True)
    referring_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    priority    = models.CharField(max_length=20, choices=PRIORITIES, default='Normal')
    photo       = models.ImageField(upload_to='photos/', null=True, blank=True)
    custom_display_id = models.CharField(max_length=50, blank=True, help_text='Custom ID on reports')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-registered_at']

    def save(self, *args, **kwargs):
        if not self.patient_id:
            last = Patient.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.patient_id = f"IPL-{n:04d}"
        super().save(*args, **kwargs)

    @property
    def full_name(self): return f"{self.first_name} {self.last_name}".strip()
    @property
    def salutation(self):
        return self.honorific
    def __str__(self): return f"{self.full_name} ({self.patient_id})"


class Booking(models.Model):
    """One booking = one visit. Can have multiple tests."""
    STATUS = [('pending','Pending'),('sample_collected','Sample Collected'),('processing','Processing'),('ready','Ready'),('delivered','Delivered')]
    PAYMENT_MODES = [('Cash','Cash'),('UPI/GPay','UPI/GPay'),('Card','Card'),('Cheque','Cheque'),('Credit','Credit')]

    receipt_id   = models.CharField(max_length=30, unique=True, editable=False)
    patient      = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bookings')
    ref_doctor   = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    tests        = models.ManyToManyField(Test, blank=True)
    booking_date = models.DateField(default=datetime.date.today)
    sample_date  = models.DateField(default=datetime.date.today)
    status       = models.CharField(max_length=20, choices=STATUS, default='sample_collected')

    # Billing
    subtotal     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    referral_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='Cash')

    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bookings_created')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_id:
            today = datetime.date.today()
            last = Booking.objects.filter(booking_date__year=today.year).order_by('id').last()
            n = (last.id if last else 0) + 1
            self.receipt_id = f"RCP-{today.year}-{n:04d}"
        super().save(*args, **kwargs)

    def recalculate(self):
        self.subtotal = sum(t.price for t in self.tests.all())
        disc = self.subtotal * self.discount_pct / 100
        self.discount_amt = disc
        self.total = self.subtotal - disc
        self.due = self.total - self.paid
        self.save()

    def __str__(self): return f"{self.receipt_id} -- {self.patient.full_name}"


class Report(models.Model):
    """One report per test per booking."""
    report_id   = models.CharField(max_length=30, unique=True, editable=False)
    booking     = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reports')
    test        = models.ForeignKey(Test, on_delete=models.CASCADE)
    report_date = models.DateField(default=datetime.date.today)
    remarks     = models.TextField(blank=True)
    sample_drawn_date    = models.DateField(null=True, blank=True)
    sample_received_date = models.DateField(null=True, blank=True)
    result_reported_date = models.DateField(null=True, blank=True)
    custom_report_no     = models.CharField(max_length=50, blank=True)
    is_finalized= models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.report_id:
            today = datetime.date.today()
            last = Report.objects.filter(report_date__year=today.year).order_by('id').last()
            n = (last.id if last else 0) + 1
            self.report_id = f"RPT-{today.year}-{n:04d}"
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.report_id} -- {self.test.name}"


class ReportResult(models.Model):
    FLAGS = [('normal','Normal'),('high','High ↑'),('low','Low ↓'),('text','Text'),('critical','Critical')]

    report      = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='results')
    parameter   = models.ForeignKey(TestParameter, on_delete=models.CASCADE, null=True, blank=True)
    param_name  = models.CharField(max_length=200)   # denormalized for display
    value       = models.CharField(max_length=200, blank=True)
    unit        = models.CharField(max_length=50, blank=True)
    lower_limit = models.FloatField(null=True, blank=True)
    upper_limit = models.FloatField(null=True, blank=True)
    flag        = models.CharField(max_length=10, choices=FLAGS, default='normal')
    sort_order  = models.PositiveIntegerField(default=0)

    class Meta: ordering = ['sort_order']

    @property
    def normal_range(self):
        if self.lower_limit is not None and self.upper_limit is not None:
            return f"{self.lower_limit} - {self.upper_limit}"
        return "--"

    def compute_flag(self):
        if not self.value: return 'normal'
        try:
            v = float(self.value)
            if self.lower_limit is not None and v < self.lower_limit: return 'low'
            if self.upper_limit is not None and v > self.upper_limit: return 'high'
            return 'normal'
        except ValueError:
            return 'text'


class LabSettings(models.Model):
    """Singleton model -- one record stores all lab branding/customization."""
    lab_name        = models.CharField(max_length=200, default='Indian Path-Lab')
    tagline         = models.CharField(max_length=200, default='AN ISO 9001:2015 CERTIFIED LAB')
    unit_text       = models.CharField(max_length=200, default='A UNIT OF PMEGP GOVT. OF INDIA')
    nabl_text       = models.CharField(max_length=300, blank=True, default='NABL',
                                       help_text='Accreditation/certification text (e.g. NABL, ISO 9001:2015). Shown on reports.')
    pro_suite_password = models.CharField(max_length=100, default='Jatin123',
                                          help_text='Password to unlock Pro Suite (Payments, Finance, etc.)')
    email           = models.EmailField(default='indianpathlab@gmail.com')
    phone           = models.CharField(max_length=100, default='9213303786, 9971404170')
    address         = models.TextField(default='C-451, Gali No. 5, Old Mustafabad,\n(Lovely Public School Market)\nNear Tirpal Factory, DELHI-110094')
    # Logo & Signature uploads
    logo_image      = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Upload lab logo (shown in PDF header)')
    letterhead_image= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Full letterhead image (replaces entire header in PDF if set)')
    signature_ansari= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. M. Ahmad Ansari signature image')
    signature_saleem= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. M. Saleem signature image')
    signature_kumar = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='N. Kumar signature image')
    signature_maurya= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. V.P. Maurya signature image')
    # Signer names & designations (editable)
    signer1_name    = models.CharField(max_length=100, default='Dr. M. SALEEM')
    signer1_qual    = models.CharField(max_length=200, default='(MD)\n(LabIncharge)')
    signer2_name    = models.CharField(max_length=100, default='N.KUMAR')
    signer2_qual    = models.CharField(max_length=200, default='(MLT)\n(Sr.Lab Tech.)')
    signer3_name    = models.CharField(max_length=100, default='Dr. V.P.MAURYA')
    signer3_qual    = models.CharField(max_length=200, default='MBBS(AM),B.Sc. MLT\n(Sr.Lab Tech.)')
    signer4_name    = models.CharField(max_length=100, default='Dr. M. AHMAD ANSARI')
    signer4_qual    = models.CharField(max_length=200, default='Consultant Biochemistry\nPhD.( AIIMS)')
    signer_image_height = models.PositiveIntegerField(default=30, help_text='Signature image height in PDF/Print (px). Controls size of uploaded signature images.')
    report_font_size    = models.PositiveIntegerField(default=12, help_text='Base font size for printed/PDF reports (pt). Recommended: 10–14.')
    # Footer image upload
    footer_image    = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Footer letterhead image (shown at bottom of PDF)')
    # PDF footer/header customization
    pdf_footer_text = models.TextField(blank=True,
                                       default='Note : Above Mentioned Finding Are Professional Opinion and Not a Final Diagnosis All Laboratory Test & Other Investigation Results are to be Corelate Clinical Pathology. Discrepancies if any Necessitate Review Repeat of the Test Contact, Laboratory Immediately This Report is for the perusal for physician/Doctors only.\nNot Valid for Medico Legal Purpose (Court Cases)')
    pdf_footer_image= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Optional footer image/stamp')
    pdf_header_image= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='PDF Header image -- shown at top of PDF & Bulk PDF (not in direct print)')
    # -- Print / PDF Margin Settings (top, right, bottom, left in mm) --
    # Single report
    print_single_margin_top    = models.PositiveIntegerField(default=100, help_text='Single Print - Top margin (px)')
    print_single_margin_bottom = models.PositiveIntegerField(default=96,  help_text='Single Print - Bottom margin (px)')
    print_single_margin_left   = models.PositiveIntegerField(default=0,   help_text='Single Print - Left margin (px)')
    print_single_margin_right  = models.PositiveIntegerField(default=0,   help_text='Single Print - Right margin (px)')
    pdf_single_margin_top      = models.PositiveIntegerField(default=0,   help_text='Single PDF - Top margin (px)')
    pdf_single_margin_bottom   = models.PositiveIntegerField(default=0,   help_text='Single PDF - Bottom margin (px)')
    pdf_single_margin_left     = models.PositiveIntegerField(default=0,   help_text='Single PDF - Left margin (px)')
    pdf_single_margin_right    = models.PositiveIntegerField(default=0,   help_text='Single PDF - Right margin (px)')
    # Bulk report
    print_bulk_margin_top      = models.PositiveIntegerField(default=100, help_text='Bulk Print - Top margin (px)')
    print_bulk_margin_bottom   = models.PositiveIntegerField(default=96,  help_text='Bulk Print - Bottom margin (px)')
    print_bulk_margin_left     = models.PositiveIntegerField(default=0,   help_text='Bulk Print - Left margin (px)')
    print_bulk_margin_right    = models.PositiveIntegerField(default=0,   help_text='Bulk Print - Right margin (px)')
    pdf_bulk_margin_top        = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Top margin (px)')
    pdf_bulk_margin_bottom     = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Bottom margin (px)')
    pdf_bulk_margin_left       = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Left margin (px)')
    pdf_bulk_margin_right      = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Right margin (px)')
    # Bill
    print_bill_margin_top      = models.PositiveIntegerField(default=100, help_text='Bill Print - Top margin (px)')
    print_bill_margin_bottom   = models.PositiveIntegerField(default=96,  help_text='Bill Print - Bottom margin (px)')
    print_bill_margin_left     = models.PositiveIntegerField(default=0,   help_text='Bill Print - Left margin (px)')
    print_bill_margin_right    = models.PositiveIntegerField(default=0,   help_text='Bill Print - Right margin (px)')
    pdf_bill_margin_top        = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Top margin (px)')
    pdf_bill_margin_bottom     = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Bottom margin (px)')
    pdf_bill_margin_left       = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Left margin (px)')
    pdf_bill_margin_right      = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Right margin (px)')

    show_timing_bar = models.BooleanField(default=True, help_text='Show timing bar in PDF')
    timing_text     = models.CharField(max_length=200, default='Timing : 9 A.M. to 9 P.M. (Sunday Evening Closed)')
    facilities_text = models.TextField(default='Facilities : X-Ray, E.C.G., Examination of Blood, Urine, Stool, Sputum, Semen & All Spl. Test')
    # -- SMS / WhatsApp Settings ----------------------------------------------
    sms_provider        = models.CharField(max_length=20, default='none',
                            choices=[('none','Disabled'),('msg91','MSG91'),('twilio','Twilio')],
                            help_text='SMS provider to use')
    msg91_auth_key      = models.CharField(max_length=200, blank=True, help_text='MSG91 Auth Key')
    msg91_sender_id     = models.CharField(max_length=10, blank=True, default='IPLABS', help_text='6-char DLT Sender ID')
    msg91_template_id   = models.CharField(max_length=100, blank=True, help_text='MSG91 DLT Template ID')
    twilio_account_sid  = models.CharField(max_length=100, blank=True)
    twilio_auth_token   = models.CharField(max_length=100, blank=True)
    twilio_from_number  = models.CharField(max_length=20, blank=True, help_text='Twilio phone number e.g. +1234567890')
    whatsapp_enabled    = models.BooleanField(default=False)
    whatsapp_token      = models.CharField(max_length=300, blank=True, help_text='Meta Cloud API access token')
    whatsapp_phone_id   = models.CharField(max_length=100, blank=True, help_text='Meta phone number ID')
    # -- Razorpay Payment Settings ---------------------------------------------
    razorpay_key_id      = models.CharField(max_length=100, blank=True, help_text='Razorpay Key ID (rzp_live_... or rzp_test_...)')
    razorpay_key_secret  = models.CharField(max_length=100, blank=True, help_text='Razorpay Key Secret')
    razorpay_webhook_secret = models.CharField(max_length=100, blank=True, help_text='Razorpay Webhook Secret')
    # -- HIS/HL7 Integration Settings -----------------------------------------
    his_endpoint_url    = models.CharField(max_length=300, blank=True, help_text='HIS HL7 endpoint URL for sending lab results')
    his_auth_token      = models.CharField(max_length=200, blank=True, help_text='Bearer token for HIS authentication')
    # -- AI Interpretation Settings --------------------------------------------
    ai_auto_interpret   = models.BooleanField(default=True, help_text='Auto-generate AI interpretation on report finalization')
    openai_api_key      = models.CharField(max_length=200, blank=True, help_text='OpenAI API key for GPT-powered interpretation (optional)')
    # -- Landing Page Content (editable) --------------------------------------
    landing_patients  = models.CharField(max_length=20, default='5000+', help_text='Hero stat: patients served')
    landing_tests     = models.CharField(max_length=20, default='200+',  help_text='Hero stat: tests available')
    landing_years     = models.CharField(max_length=20, default='10+',   help_text='Hero stat: years experience')
    about_text        = models.TextField(blank=True, default='We are committed to providing accurate, reliable and timely diagnostic services.')
    services_text     = models.TextField(blank=True, default='Comprehensive range of pathology tests covering all major specialties.')
    # -- Feedback destination --------------------------------------------------
    feedback_email    = models.EmailField(blank=True, help_text='Email to receive feedback submissions (optional)')
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lab Settings'
        verbose_name_plural = 'Lab Settings'

    def __str__(self): return 'Lab Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TestNote(models.Model):
    """Per-test custom notes that appear at the bottom of the report."""
    test      = models.OneToOneField(Test, on_delete=models.CASCADE, related_name='note')
    note_text = models.TextField(help_text='Note printed at bottom of this test report (e.g. cell morphology note for CBC)')
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self): return f"Note: {self.test.name}"


# ===============================================================================
# FEATURE 1: MULTI-BRANCH SUPPORT
# ===============================================================================

class Branch(models.Model):
    """Multi-branch support -- each lab location is a Branch."""
    branch_id   = models.CharField(max_length=20, unique=True, editable=False)
    name        = models.CharField(max_length=200)
    address     = models.TextField(blank=True)
    phone       = models.CharField(max_length=100, blank=True)
    email       = models.EmailField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.branch_id:
            last = Branch.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.branch_id = f"BR-{n:03d}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name

    class Meta:
        verbose_name_plural = 'Branches'


# ===============================================================================
# FEATURE 2: SMS / WHATSAPP NOTIFICATIONS
# ===============================================================================

class NotificationLog(models.Model):
    """Tracks all SMS / WhatsApp messages sent to patients."""
    CHANNELS = [('sms','SMS'),('whatsapp','WhatsApp')]
    STATUS   = [('sent','Sent'),('delivered','Delivered'),('failed','Failed'),('pending','Pending')]

    patient      = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='notifications')
    channel      = models.CharField(max_length=20, choices=CHANNELS, default='sms')
    mobile       = models.CharField(max_length=20)
    message      = models.TextField()
    status       = models.CharField(max_length=20, choices=STATUS, default='pending')
    provider_ref = models.CharField(max_length=100, blank=True, help_text='Provider message ID')
    error_msg    = models.TextField(blank=True)
    sent_at      = models.DateTimeField(auto_now_add=True)
    related_report = models.ForeignKey('Report', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta: ordering = ['-sent_at']
    def __str__(self): return f"{self.channel.upper()} -> {self.mobile} [{self.status}]"


# ===============================================================================
# FEATURE 3: ONLINE PAYMENT GATEWAY (Razorpay)
# ===============================================================================

class PaymentOrder(models.Model):
    """Tracks Razorpay payment orders linked to bookings."""
    STATUS = [
        ('created','Created'),('attempted','Attempted'),
        ('paid','Paid'),('failed','Failed'),('refunded','Refunded'),
    ]
    booking           = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='payment_orders')
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True)
    amount            = models.DecimalField(max_digits=10, decimal_places=2)
    currency          = models.CharField(max_length=5, default='INR')
    status            = models.CharField(max_length=20, choices=STATUS, default='created')
    created_at        = models.DateTimeField(auto_now_add=True)
    paid_at           = models.DateTimeField(null=True, blank=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"{self.razorpay_order_id} -- ₹{self.amount} [{self.status}]"


# ===============================================================================
# FEATURE 4: INSURANCE CLAIM PROCESSING
# ===============================================================================

class InsuranceCompany(models.Model):
    name       = models.CharField(max_length=200)
    tpa_name   = models.CharField(max_length=200, blank=True, help_text='Third Party Administrator name')
    contact    = models.CharField(max_length=100, blank=True)
    email      = models.EmailField(blank=True)
    is_active  = models.BooleanField(default=True)

    class Meta: ordering = ['name']
    def __str__(self): return self.name


class InsuranceClaim(models.Model):
    """Insurance claim linked to a booking."""
    STATUSES = [
        ('draft','Draft'),('submitted','Submitted'),
        ('under_review','Under Review'),('approved','Approved'),
        ('rejected','Rejected'),('settled','Settled'),
    ]
    claim_no       = models.CharField(max_length=50, unique=True, editable=False)
    booking        = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='insurance_claims')
    insurance_co   = models.ForeignKey(InsuranceCompany, on_delete=models.SET_NULL, null=True)
    policy_number  = models.CharField(max_length=100, blank=True)
    member_id      = models.CharField(max_length=100, blank=True)
    claim_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    approved_amount= models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUSES, default='draft')
    remarks        = models.TextField(blank=True)
    submitted_at   = models.DateTimeField(null=True, blank=True)
    settled_at     = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.claim_no:
            last = InsuranceClaim.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.claim_no = f"CLM-{n:05d}"
        super().save(*args, **kwargs)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"{self.claim_no} -- {self.booking.receipt_id}"


# ===============================================================================
# FEATURE 5: HL7/FHIR INTEGRATION LOG
# ===============================================================================

class HL7FHIRLog(models.Model):
    """Log of all HL7/FHIR messages sent/received with HIS."""
    DIRECTIONS = [('outbound','Outbound (to HIS)'),('inbound','Inbound (from HIS)')]
    TYPES      = [('ORU_R01','ORU^R01 -- Lab Result'),('ORM_O01','ORM^O01 -- Order'),
                  ('ADT_A01','ADT^A01 -- Admission'),('FHIR_Bundle','FHIR Bundle'),
                  ('FHIR_DiagReport','FHIR DiagnosticReport')]

    direction   = models.CharField(max_length=20, choices=DIRECTIONS)
    msg_type    = models.CharField(max_length=30, choices=TYPES)
    patient     = models.ForeignKey('Patient', on_delete=models.SET_NULL, null=True, blank=True)
    report      = models.ForeignKey('Report', on_delete=models.SET_NULL, null=True, blank=True)
    raw_message = models.TextField(blank=True, help_text='Full HL7/FHIR message payload')
    status      = models.CharField(max_length=20, default='sent',
                    choices=[('sent','Sent'),('ack','Acknowledged'),('error','Error')])
    error_detail= models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"{self.msg_type} {self.direction} [{self.status}]"


# ===============================================================================
# FEATURE 6: MACHINE INTERFACE (Lab Analyser Auto-Import)
# ===============================================================================

class AnalyserInterface(models.Model):
    """Configuration for connected lab analyser machines."""
    PROTOCOLS = [('ASTM','ASTM E1394'),('HL7','HL7 2.x'),('CSV','CSV/TXT file'),
                 ('SERIAL','Serial port'),('TCP','TCP/IP socket')]
    name       = models.CharField(max_length=100, help_text='e.g. Sysmex XN-1000, Mindray BC-5380')
    protocol   = models.CharField(max_length=20, choices=PROTOCOLS, default='ASTM')
    host       = models.CharField(max_length=200, blank=True, help_text='IP address or COM port')
    port       = models.PositiveIntegerField(null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    test_mapping = models.TextField(blank=True,
        help_text='JSON: {"MACHINE_PARAM": "TestParameter_pk"} -- maps machine codes to test params')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.name} ({self.protocol})"


class AnalyserResult(models.Model):
    """Raw result received from a lab analyser machine."""
    STATUS = [('pending','Pending import'),('imported','Imported to report'),
              ('error','Import error'),('ignored','Ignored')]
    analyser      = models.ForeignKey(AnalyserInterface, on_delete=models.SET_NULL, null=True)
    sample_id     = models.CharField(max_length=100, help_text='Barcode / Sample ID from machine')
    raw_data      = models.TextField(help_text='Raw ASTM/HL7 message from machine')
    parsed_json   = models.TextField(blank=True, help_text='Parsed result as JSON')
    status        = models.CharField(max_length=20, choices=STATUS, default='pending')
    linked_report = models.ForeignKey('Report', on_delete=models.SET_NULL, null=True, blank=True)
    error_detail  = models.TextField(blank=True)
    received_at   = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-received_at']
    def __str__(self): return f"Sample {self.sample_id} from {self.analyser}"


# ===============================================================================
# FEATURE 7 & 8: AI DIAGNOSTIC INTERPRETATION + MOBILE APP TOKEN
# ===============================================================================

class AIInterpretation(models.Model):
    """AI/ML generated diagnostic interpretation for a report."""
    STATUS = [('pending','Pending'),('generated','Generated'),('reviewed','Reviewed'),('approved','Approved')]

    report        = models.OneToOneField('Report', on_delete=models.CASCADE, related_name='ai_interpretation')
    interpretation= models.TextField(blank=True, help_text='AI generated clinical interpretation text')
    flags_summary = models.TextField(blank=True, help_text='Summary of abnormal parameters')
    severity      = models.CharField(max_length=20, blank=True,
                      choices=[('normal','Normal'),('mild','Mild concern'),
                               ('moderate','Moderate concern'),('critical','Critical')])
    status        = models.CharField(max_length=20, choices=STATUS, default='pending')
    reviewed_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    model_used    = models.CharField(max_length=100, default='rule-based-v1')
    generated_at  = models.DateTimeField(auto_now_add=True)
    reviewed_at   = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f"AI Interpretation -- {self.report.report_id}"


class MobileDeviceToken(models.Model):
    """FCM/APNs push notification tokens for mobile app users."""
    PLATFORMS = [('android','Android'),('ios','iOS')]
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token     = models.TextField(help_text='FCM or APNs device token')
    platform  = models.CharField(max_length=10, choices=PLATFORMS, default='android')
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.user.username} -- {self.platform}"


# ===============================================================================
# TEST PROFILES (Panels) -- e.g. Fever Profile, Liver Profile 1.1, KFT, LFT
# ===============================================================================

class TestProfile(models.Model):
    """A named bundle of tests -- e.g. 'Fever Profile', 'LFT', 'KFT 1.1'."""
    profile_code = models.CharField(max_length=30, unique=True, editable=False)
    name         = models.CharField(max_length=200, help_text='e.g. Fever Profile, LFT 1.1')
    short_code   = models.CharField(max_length=20, blank=True, help_text='e.g. FP, LFT, KFT')
    description  = models.TextField(blank=True)
    tests        = models.ManyToManyField(Test, blank=True, related_name='profiles')
    price        = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                     help_text='Profile price (can be less than sum of individual tests)')
    is_active    = models.BooleanField(default=True)
    sort_order   = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.profile_code:
            last = TestProfile.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.profile_code = f"PRF-{n:03d}"
        super().save(*args, **kwargs)

    @property
    def test_count(self):
        return self.tests.count()

    @property
    def total_mrp(self):
        return sum(t.price for t in self.tests.all())

    @property
    def discount_pct(self):
        if self.total_mrp > 0:
            return round((1 - self.price / self.total_mrp) * 100, 1)
        return 0

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Test Profile'

    def __str__(self): return f"{self.name} ({self.profile_code})"


# ===============================================================================
# SAMPLE COLLECTION TRACKING
# ===============================================================================

class SampleCollection(models.Model):
    """Tracks sample tube/container details for a booking."""
    TUBE_TYPES = [
        ('EDTA','EDTA (Purple cap)'),('Plain','Plain (Red cap)'),
        ('Fluoride','Fluoride (Grey cap)'),('Citrate','Sodium Citrate (Blue cap)'),
        ('Heparin','Heparin (Green cap)'),('SST','SST (Gold cap)'),
        ('Urine','Urine container'),('Stool','Stool container'),
        ('Other','Other'),
    ]
    STATUS = [('pending','Pending'),('collected','Collected'),('received','Lab Received'),
              ('rejected','Rejected'),('processing','Processing')]

    booking       = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='samples')
    tube_type     = models.CharField(max_length=30, choices=TUBE_TYPES)
    tube_count    = models.PositiveIntegerField(default=1)
    barcode       = models.CharField(max_length=50, blank=True)
    collected_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_collected')
    collected_at  = models.DateTimeField(null=True, blank=True)
    received_at   = models.DateTimeField(null=True, blank=True)
    status        = models.CharField(max_length=20, choices=STATUS, default='pending')
    remarks       = models.CharField(max_length=200, blank=True)
    temperature   = models.CharField(max_length=20, blank=True, help_text='e.g. Room temp, 4°C, Frozen')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['created_at']
    def __str__(self): return f"{self.tube_type} -- {self.booking.receipt_id}"


# ===============================================================================
# HOME COLLECTION / PHLEBOTOMIST
# ===============================================================================

class HomeCollection(models.Model):
    """Home sample collection request."""
    STATUS = [('scheduled','Scheduled'),('assigned','Assigned'),('collected','Collected'),
              ('cancelled','Cancelled')]

    booking        = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='home_collection')
    address        = models.TextField()
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    phlebotomist   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                       related_name='home_collections')
    status         = models.CharField(max_length=20, choices=STATUS, default='scheduled')
    collection_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    remarks        = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-scheduled_date', '-scheduled_time']
    def __str__(self): return f"Home Collection -- {self.booking.receipt_id} on {self.scheduled_date}"


# ===============================================================================
# REFERRAL DOCTOR COMMISSION TRACKING
# ===============================================================================

class DoctorCommission(models.Model):
    """Monthly commission record for referring doctors."""
    STATUS = [('pending','Pending'),('paid','Paid'),('hold','On Hold')]
    doctor      = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='commissions')
    month       = models.DateField(help_text='First day of the commission month')
    bookings    = models.ManyToManyField(Booking, blank=True)
    total_billing = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_pct= models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amt= models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status      = models.CharField(max_length=20, choices=STATUS, default='pending')
    paid_on     = models.DateField(null=True, blank=True)
    remarks     = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-month']
    def __str__(self): return f"Commission -- Dr. {self.doctor.name} -- {self.month.strftime('%b %Y')}"


# ===============================================================================
# EXPENDITURE / REAGENT TRACKING
# ===============================================================================

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Expenditure(models.Model):
    """Lab expense tracking -- reagents, equipment, salaries, misc."""
    PAYMENT_MODES = [('Cash','Cash'),('Bank Transfer','Bank Transfer'),
                     ('Cheque','Cheque'),('UPI','UPI')]
    date        = models.DateField()
    category    = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=300)
    vendor      = models.CharField(max_length=200, blank=True)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode= models.CharField(max_length=30, choices=PAYMENT_MODES, default='Cash')
    invoice_no  = models.CharField(max_length=100, blank=True)
    added_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-date']
    def __str__(self): return f"{self.description} -- ₹{self.amount} on {self.date}"


# ===============================================================================
# INVENTORY / REAGENT STOCK
# ===============================================================================

class InventoryItem(models.Model):
    """Lab reagents, consumables, equipment inventory."""
    UNITS = [('units','Units'),('ml','mL'),('L','Litre'),('g','Gram'),
             ('kg','Kg'),('strips','Strips'),('vials','Vials'),('boxes','Boxes')]
    name         = models.CharField(max_length=200)
    category     = models.CharField(max_length=100, blank=True, help_text='e.g. Reagent, Consumable, Equipment')
    vendor       = models.CharField(max_length=200, blank=True)
    unit         = models.CharField(max_length=20, choices=UNITS, default='units')
    current_stock= models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock    = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                     help_text='Alert when stock falls below this level')
    unit_cost    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_restocked = models.DateField(null=True, blank=True)
    expiry_date  = models.DateField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock

    @property
    def is_expired(self):
        import datetime
        return self.expiry_date and self.expiry_date < datetime.date.today()

    class Meta: ordering = ['category', 'name']
    def __str__(self): return f"{self.name} ({self.current_stock} {self.unit})"


# ===============================================================================
# PATIENT VISIT HISTORY / OPD REGISTER
# ===============================================================================

class PatientNote(models.Model):
    """Clinical notes/remarks on a patient for internal reference."""
    patient   = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='notes')
    note      = models.TextField()
    note_type = models.CharField(max_length=30, default='general',
                  choices=[('general','General'),('clinical','Clinical'),
                           ('allergy','Allergy/Alert'),('billing','Billing')])
    added_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at= models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Note -- {self.patient.full_name}"


# ===============================================================================
# QUALITY CONTROL (QC) LOG
# ===============================================================================

class QCLog(models.Model):
    """Daily Quality Control log for lab instruments."""
    RESULTS = [('pass','Pass OK'),('fail','Fail X'),('repeat','Repeat needed')]
    date         = models.DateField()
    instrument   = models.CharField(max_length=100, help_text='e.g. Sysmex XN-1000, Chemistry Analyser')
    test_name    = models.CharField(max_length=100, help_text='e.g. CBC Control, Glucose QC')
    control_level= models.CharField(max_length=50, blank=True, help_text='e.g. Low, Normal, High')
    expected_value = models.CharField(max_length=50, blank=True)
    obtained_value = models.CharField(max_length=50, blank=True)
    result       = models.CharField(max_length=20, choices=RESULTS, default='pass')
    remarks      = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-date']
    def __str__(self): return f"QC -- {self.instrument} -- {self.date} -- {self.result}"


# ===============================================================================
# CRITICAL VALUE ALERTS
# ===============================================================================

class CriticalValueAlert(models.Model):
    """When a report result is critically abnormal -- must notify doctor."""
    STATUS = [('pending','Pending'),('notified','Doctor Notified'),('acknowledged','Acknowledged')]
    report      = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='critical_alerts')
    parameter   = models.CharField(max_length=200)
    value       = models.CharField(max_length=100)
    normal_range= models.CharField(max_length=100, blank=True)
    notified_to = models.CharField(max_length=200, blank=True, help_text='Doctor/nurse name notified')
    notified_via= models.CharField(max_length=50, blank=True, help_text='Phone/WhatsApp/In-person')
    status      = models.CharField(max_length=20, choices=STATUS, default='pending')
    created_at  = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta: ordering = ['-created_at']
    def __str__(self): return f"Critical -- {self.parameter}: {self.value} -- {self.report.report_id}"
