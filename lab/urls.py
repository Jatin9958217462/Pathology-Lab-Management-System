"""
urls.py -- PathLab v1.1
===============================================================================
URL configuration for the PathLab lab application.

All paths are relative to the app root (typically /).
Route groups:
  /login, /logout, /register       Authentication
  /dashboard/                       Main dashboard
  /patients/                        Patient management
  /booking/, /bookings/             Test bookings
  /report/                          Report entry, PDF, print
  /reports/                         Reports list, bulk PDF/print
  /doctors/                         Referring doctor management
  /tests/, /test-profiles/          Test catalog
  /staff/                           Staff & user management
  /settings/                        Lab settings
  /commissions/                     Doctor commissions
  /my-reports/                      Patient / doctor portal
  /                                 Public landing page
VERSION: 1.1
===============================================================================
"""

from django.urls import path
from . import views

urlpatterns = [
    # -- Authentication --------------------------------------------------------
    path('',            views.home,          name='home'),
    path('login/',      views.login_view,    name='login'),
    path('logout/',     views.logout_view,   name='logout'),
    path('register/',   views.register_view, name='register'),

    # Dashboard
    path('dashboard/',  views.dashboard,     name='dashboard'),

    # Patients
    path('patients/',                views.patients_list,    name='patients'),
    path('patients/add/',            views.patient_add,      name='patient_add'),
    path('patients/<int:pk>/edit/',  views.patient_edit,     name='patient_edit'),
    path('patients/<int:pk>/delete/',views.patient_delete,   name='patient_delete'),

    # Bookings
    path('booking/new/',                    views.booking_new,        name='booking_new'),
    path('booking/new/<int:pt_pk>/',        views.booking_new,        name='booking_new_pt'),
    path('booking/<int:pk>/',               views.booking_detail,     name='booking_detail'),
    path('booking/<int:pk>/update-status/', views.booking_status,     name='booking_status'),
    path('booking/<int:pk>/bill-pdf/',      views.bill_pdf,           name='bill_pdf'),
    path('booking/<int:pk>/bill-print/',    views.bill_print,         name='bill_print'),

    # Reports
    path('report/<int:report_pk>/entry/',           views.report_entry,           name='report_entry'),
    path('report/<int:report_pk>/view/',            views.report_view,            name='report_view'),
    path('report/<int:report_pk>/pdf/',             views.report_pdf,             name='report_pdf'),
    path('report/<int:report_pk>/print/',           views.report_print_direct,    name='report_print'),
    path('report/<int:report_pk>/print-margins/',   views.report_print_margins,   name='report_print_margins'),
    path('report/<int:report_pk>/pdf-zero/',        views.report_pdf_zero,        name='report_pdf_zero'),
    path('report/<int:report_pk>/finalize/',        views.report_finalize,        name='report_finalize'),
    path('report/<int:report_pk>/delete/',          views.report_delete,          name='report_delete'),
    path('result/<int:result_pk>/edit/',            views.result_inline_edit,     name='result_inline_edit'),
    path('reports/',                                views.reports_list,           name='reports'),
    path('reports/bulk-pdf/',                       views.bulk_report_pdf,        name='bulk_report_pdf'),
    path('reports/bulk-print/',                     views.bulk_report_print,      name='bulk_report_print'),

    # Doctors
    path('doctors/',               views.doctors_list,     name='doctors'),
    path('doctors/add/',           views.doctor_add,       name='doctor_add'),
    path('doctors/<int:pk>/delete/',     views.doctor_delete,     name='doctor_delete'),
    path('doctors/<int:pk>/connect/',    views.doctor_connect,    name='doctor_connect'),
    path('doctors/<int:pk>/disconnect/', views.doctor_disconnect, name='doctor_disconnect'),

    # Staff / User Management (Admin only)
    path('staff/',                          views.staff_list,           name='staff_list'),
    path('staff/add/',                      views.staff_add,            name='staff_add'),
    path('staff/<int:pk>/delete/',          views.staff_delete,         name='staff_delete'),
    path('staff/<int:pk>/reset-password/',  views.staff_reset_password, name='staff_reset_password'),

    # Tests
    path('tests/',                  views.tests_list,      name='tests'),
    path('tests/add/',              views.test_add,        name='test_add'),
    path('tests/<int:pk>/delete/',  views.test_delete,     name='test_delete'),
    path('tests/<int:pk>/params/',  views.test_params,     name='test_params'),
    path('tests/<int:pk>/note/',    views.test_note_save,  name='test_note_save'),
    path('rate-list/',              views.rate_list,       name='rate_list'),

    # Lab Settings
    path('settings/',        views.lab_settings,      name='lab_settings'),
    path('settings/save/',   views.lab_settings_save, name='lab_settings_save'),

    # Search
    path('search/',          views.advanced_search,   name='advanced_search'),

    # Patient portal
    path('my-reports/',      views.my_reports,        name='my_reports'),

    # AJAX
    path('api/patient/<int:pk>/',        views.api_patient,      name='api_patient'),
    path('api/booking-tests/<int:pk>/',  views.api_booking_tests,name='api_booking_tests'),

    # Chatbot
    path('chatbot/', views.chatbot, name='chatbot'),

    # -- FEATURE: Multi-branch ----------------------------------------------
    path('branches/',               views.branches_list,  name='branches'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),

    # -- FEATURE: SMS/WhatsApp Notifications -------------------------------
    path('notifications/',                          views.notifications_list,  name='notifications'),
    path('report/<int:report_pk>/send-sms/',        views.send_report_sms,     name='send_report_sms'),

    # -- FEATURE: Online Payment (Razorpay) --------------------------------
    path('payment/create-order/<int:booking_pk>/',  views.payment_create_order, name='payment_create_order'),
    path('payment/verify/',                         views.payment_verify,       name='payment_verify'),
    path('payment/webhook/',                        views.payment_webhook,      name='payment_webhook'),
    path('payments/',                               views.payments_list,        name='payments_list'),

    # -- FEATURE: Insurance Claims -----------------------------------------
    path('insurance/claims/',                       views.insurance_claims_list,  name='insurance_claims'),
    path('insurance/claim/new/<int:booking_pk>/',   views.insurance_claim_new,    name='insurance_claim_new'),
    path('insurance/claim/<int:pk>/',               views.insurance_claim_detail, name='insurance_claim_detail'),
    path('insurance/companies/',                    views.insurance_companies_list, name='insurance_companies'),

    # -- FEATURE: HL7/FHIR -------------------------------------------------
    path('hl7/log/',                                views.hl7_fhir_log,         name='hl7_fhir_log'),
    path('report/<int:report_pk>/fhir-export/',     views.fhir_export_report,   name='fhir_export_report'),
    path('report/<int:report_pk>/hl7-send/',        views.hl7_send_report,      name='hl7_send_report'),

    # -- FEATURE: Machine Analyser Interface -------------------------------
    path('analyser/',                               views.analyser_list,          name='analyser_list'),
    path('analyser/add/',                           views.analyser_add,           name='analyser_add'),
    path('analyser/upload-csv/',                    views.analyser_upload_csv,    name='analyser_upload_csv'),
    path('analyser/import/<int:result_pk>/',        views.analyser_import_result, name='analyser_import_result'),

    # -- FEATURE: AI Interpretation ----------------------------------------
    path('report/<int:report_pk>/ai/',              views.ai_interpretation,         name='ai_interpretation'),
    path('report/<int:report_pk>/ai/approve/',      views.ai_interpretation_approve, name='ai_interpretation_approve'),

    # -- FEATURE: Mobile App API -------------------------------------------
    path('api/mobile/register-token/',              views.mobile_register_token, name='mobile_register_token'),
    path('api/mobile/reports/',                     views.mobile_api_reports,    name='mobile_api_reports'),

    # -- Test Profiles (Panels) ------------------------------------------------
    path('test-profiles/',                  views.test_profiles,         name='test_profiles'),
    path('test-profiles/add/',              views.test_profile_add,      name='test_profile_add'),
    path('test-profiles/<int:pk>/edit/',    views.test_profile_edit,     name='test_profile_edit'),
    path('test-profiles/<int:pk>/delete/',  views.test_profile_delete,   name='test_profile_delete'),
    path('api/profile/<int:pk>/tests/',     views.api_profile_tests,     name='api_profile_tests'),

    # -- Home Collection -------------------------------------------------------
    path('home-collections/',                         views.home_collections,    name='home_collections'),
    path('home-collection/add/<int:booking_pk>/',     views.home_collection_add, name='home_collection_add'),

    # -- Doctor Commission -----------------------------------------------------
    path('commissions/',          views.doctor_commissions,        name='doctor_commissions'),
    path('commissions/generate/', views.doctor_commission_generate,name='commission_generate'),
    path('commissions/<int:pk>/pay/',  views.commission_mark_paid, name='commission_pay'),
    path('commissions/<int:pk>/edit/', views.commission_edit,      name='commission_edit'),
    path('commissions/<int:pk>/pdf/',  views.commission_pdf,       name='commission_pdf'),

    # -- Expenditure -----------------------------------------------------------
    path('expenditures/',  views.expenditures,  name='expenditures'),

    # -- Inventory -------------------------------------------------------------
    path('inventory/',     views.inventory,     name='inventory'),

    # -- QC Log ----------------------------------------------------------------
    path('qc-log/',        views.qc_log,        name='qc_log'),

    # -- Critical Value Alerts -------------------------------------------------
    path('critical-alerts/',              views.critical_alerts,       name='critical_alerts'),
    path('critical-alerts/<int:pk>/resolve/', views.critical_alert_resolve, name='critical_alert_resolve'),

    # -- Revenue / Finance Report ----------------------------------------------
    path('revenue/',       views.revenue_report, name='revenue_report'),

    # -- Pro Suite PIN ---------------------------------------------------------
    path('pro-suite/lock/',   views.pro_suite_lock,   name='pro_suite_lock'),
    path('pro-suite/logout/', views.pro_suite_logout, name='pro_suite_logout'),

    # -- Public Landing Page ---------------------------------------------------
    path('welcome/',           views.landing_page,     name='landing_page'),
    path('welcome/feedback/',  views.landing_feedback, name='landing_feedback'),
]