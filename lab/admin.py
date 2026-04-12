from django.contrib import admin
from .models import UserProfile, Patient, Doctor, Test, TestParameter, Booking, Report, ReportResult

@admin.register(UserProfile)
class UPAdmin(admin.ModelAdmin):
    list_display = ['user','role','phone']
    list_filter  = ['role']

@admin.register(Patient)
class PtAdmin(admin.ModelAdmin):
    list_display = ['patient_id','full_name','age','gender','mobile','priority']
    search_fields= ['first_name','last_name','mobile','patient_id']
    readonly_fields=['patient_id']

    def full_name(self,obj): return obj.full_name

@admin.register(Doctor)
class DocAdmin(admin.ModelAdmin):
    list_display=['doc_id','name','qualification','mobile']
    search_fields=['name','mobile']

class ParamInline(admin.TabularInline):
    model=TestParameter;extra=0

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display=['name','category','price','sample','active']
    list_filter =['category','active']
    list_editable=['price','active']
    inlines=[ParamInline]

class ReportInline(admin.TabularInline):
    model=Report;extra=0;readonly_fields=['report_id']

@admin.register(Booking)
class BkAdmin(admin.ModelAdmin):
    list_display=['receipt_id','patient','total','payment_mode','status','booking_date']
    list_filter =['status','payment_mode']
    readonly_fields=['receipt_id']
    filter_horizontal=['tests']
    inlines=[ReportInline]

class ResultInline(admin.TabularInline):
    model=ReportResult;extra=0

@admin.register(Report)
class RptAdmin(admin.ModelAdmin):
    list_display=['report_id','booking','test','is_finalized','report_date']
    list_filter =['is_finalized']
    readonly_fields=['report_id']
    inlines=[ResultInline]

from .models import LabSettings, TestNote

@admin.register(LabSettings)
class LabSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Lab Identity', {'fields': ['lab_name','tagline','unit_text','email','phone','address']}),
        ('Logo & Letterhead', {'fields': ['logo_image','letterhead_image']}),
        ('Signatures', {'fields': ['signature_ansari','signature_saleem','signature_kumar','signature_maurya']}),
        ('PDF Footer', {'fields': ['pdf_footer_text','pdf_footer_image','show_timing_bar','timing_text','facilities_text']}),
    ]
    def has_add_permission(self, request):
        return not LabSettings.objects.exists()

@admin.register(TestNote)
class TestNoteAdmin(admin.ModelAdmin):
    list_display = ['test','updated_at']
    search_fields = ['test__name']

# Register new feature models
from .models import (
    Branch, NotificationLog, PaymentOrder,
    InsuranceCompany, InsuranceClaim,
    HL7FHIRLog, AnalyserInterface, AnalyserResult,
    AIInterpretation, MobileDeviceToken
)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('branch_id', 'name', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('sent_at', 'channel', 'patient', 'mobile', 'status', 'provider_ref')
    list_filter = ('channel', 'status')
    readonly_fields = ('sent_at',)

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ('razorpay_order_id', 'booking', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'paid_at')

@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'tpa_name', 'contact', 'email', 'is_active')

@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_no', 'booking', 'insurance_co', 'claim_amount', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(HL7FHIRLog)
class HL7FHIRLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'msg_type', 'direction', 'patient', 'status')
    list_filter = ('direction', 'status', 'msg_type')

@admin.register(AnalyserInterface)
class AnalyserInterfaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'protocol', 'host', 'port', 'is_active')

@admin.register(AnalyserResult)
class AnalyserResultAdmin(admin.ModelAdmin):
    list_display = ('received_at', 'sample_id', 'analyser', 'status')
    list_filter = ('status',)

@admin.register(AIInterpretation)
class AIInterpretationAdmin(admin.ModelAdmin):
    list_display = ('report', 'severity', 'status', 'model_used', 'generated_at')
    list_filter = ('severity', 'status')

@admin.register(MobileDeviceToken)
class MobileDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'registered_at')
    list_filter = ('platform', 'is_active')

from .models import (TestProfile, SampleCollection, HomeCollection, DoctorCommission,
    ExpenseCategory, Expenditure, InventoryItem, PatientNote, QCLog, CriticalValueAlert)

@admin.register(TestProfile)
class TestProfileAdmin(admin.ModelAdmin):
    list_display = ('profile_code','name','short_code','price','test_count','is_active')
    filter_horizontal = ('tests',)

@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display = ('date','description','vendor','amount','payment_mode')
    list_filter = ('payment_mode','category')

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name','category','current_stock','unit','min_stock','expiry_date','is_active')

@admin.register(QCLog)
class QCLogAdmin(admin.ModelAdmin):
    list_display = ('date','instrument','test_name','result','performed_by')
    list_filter = ('result',)

@admin.register(CriticalValueAlert)
class CriticalValueAlertAdmin(admin.ModelAdmin):
    list_display = ('created_at','report','parameter','value','status')
    list_filter = ('status',)

admin.site.register(ExpenseCategory)
admin.site.register(SampleCollection)
admin.site.register(HomeCollection)
admin.site.register(DoctorCommission)
admin.site.register(PatientNote)
