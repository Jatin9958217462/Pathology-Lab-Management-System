"""
Migration 0005 — Update Test Parameters
========================================
KFT  : Remove Sodium (Na+), Potassium (K+), Chloride (Cl-)
       Add BUN (Blood Urea Nitrogen) — auto-calculated = Urea × 0.467
LIPID: Add calculated ratio parameters matching legacy software order
LFT  : Remove GGT; A:G Ratio formula stays as Albumin ÷ Globulin
"""

from django.db import migrations


def update_kft_params(apps, schema_editor):
    Test = apps.get_model('lab', 'Test')
    TestParameter = apps.get_model('lab', 'TestParameter')

    # Find KFT test (case-insensitive match)
    for test in Test.objects.all():
        name_up = test.name.upper()
        if 'KFT' in name_up or 'KIDNEY FUNCTION' in name_up or 'RENAL' in name_up:
            # Remove Sodium, Potassium, Chloride
            removed = TestParameter.objects.filter(
                test=test,
                param_name__iregex=r'(sodium|potassium|chloride|na\+|k\+|cl-)',
            )
            removed.delete()

            # Add BUN if not already present
            if not TestParameter.objects.filter(test=test, param_name__icontains='BUN').exists():
                # Put BUN right after Uric Acid (sort order 3 → insert at 4)
                # Shift everything at sort_order >= 4 up by 1
                TestParameter.objects.filter(test=test, sort_order__gte=4).update(
                    sort_order=models.F('sort_order') + 1
                )
                TestParameter.objects.create(
                    test=test,
                    param_name='BUN',
                    unit='mg/dL',
                    lower_limit=7.0,
                    upper_limit=20.0,
                    is_text=False,
                    sort_order=4,
                )


def update_lipid_params(apps, schema_editor):
    Test = apps.get_model('lab', 'Test')
    TestParameter = apps.get_model('lab', 'TestParameter')

    for test in Test.objects.all():
        name_up = test.name.upper()
        if 'LIPID' in name_up or 'CHOLESTEROL' in name_up:
            # Remove old calculated params if any (avoid duplicates on re-run)
            TestParameter.objects.filter(
                test=test,
                param_name__iregex=r'(vldl|ldl cholest|ldl/hdl|ldl cholestrol/hdl|triglycerides/hdl|s\.cholestrol/hdl)',
            ).delete()

            # Get current max sort_order
            existing = list(TestParameter.objects.filter(test=test).order_by('sort_order'))

            # Desired final order (from Image 4):
            # 0 S.Cholestrol Total
            # 1 TRIGLYCERIDES - SERUM
            # 2 CHOLESTEROL - HDL (DIRECT)
            # 3 VLDL -VERY LOW DENSITY LI     [calculated]
            # 4 LDL Cholestrol                 [calculated]
            # 5 LDL Cholestrol/HDL Ratio       [calculated]
            # 6 Triglycerides/HDL Ratio        [calculated]
            # 7 S.Cholestrol/HDL Ratio         [calculated]

            # Re-number existing 3 params cleanly
            for i, p in enumerate(existing):
                p.sort_order = i
                p.save()

            base = len(existing)

            new_params = [
                dict(param_name='VLDL -Very Low Density Lipoprotein', unit='mg/dL',
                     lower_limit=16.0, upper_limit=43.0, sort_order=base + 0),
                dict(param_name='LDL Cholestrol', unit='mg/dL',
                     lower_limit=30.0, upper_limit=100.0, sort_order=base + 1),
                dict(param_name='LDL Cholestrol/HDL Ratio', unit='',
                     lower_limit=0.0, upper_limit=4.0, sort_order=base + 2),
                dict(param_name='Triglycerides/HDL Ratio', unit='',
                     lower_limit=0.0, upper_limit=5.9, sort_order=base + 3),
                dict(param_name='S.Cholestrol/HDL Ratio', unit='',
                     lower_limit=0.0, upper_limit=4.0, sort_order=base + 4),
            ]
            for p in new_params:
                TestParameter.objects.get_or_create(
                    test=test, param_name=p['param_name'],
                    defaults=dict(unit=p['unit'], lower_limit=p['lower_limit'],
                                  upper_limit=p['upper_limit'], is_text=False,
                                  sort_order=p['sort_order'])
                )


def update_lft_params(apps, schema_editor):
    Test = apps.get_model('lab', 'Test')
    TestParameter = apps.get_model('lab', 'TestParameter')

    for test in Test.objects.all():
        name_up = test.name.upper()
        if 'LFT' in name_up or 'LIVER FUNCTION' in name_up:
            # Remove GGT
            TestParameter.objects.filter(test=test, param_name__iregex=r'ggt|gamma').delete()


def reverse_migrations(apps, schema_editor):
    pass  # irreversible data migration — no rollback needed


# We need models.F for the KFT shift — import it at migration level
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0004_signer_names_footer_image'),
    ]

    operations = [
        migrations.RunPython(update_kft_params,  reverse_migrations),
        migrations.RunPython(update_lipid_params, reverse_migrations),
        migrations.RunPython(update_lft_params,  reverse_migrations),
    ]
