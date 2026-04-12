"""
Management Command: fix_test_params
=====================================
Run this ONCE on your existing database to update KFT, LFT, Lipid parameters.

Usage:
    python manage.py fix_test_params

What it does:
    KFT  : Removes Sodium (Na+), Potassium (K+), Chloride (Cl-)
           Adds BUN after Uric Acid  [BUN = Blood Urea × 0.467]
    LFT  : Removes GGT
           A:G Ratio = Albumin ÷ Globulin (auto-calculated, no change needed)
    LIPID: Renames existing params to match Image-4 standard names
           Adds: LDL Cholestrol/HDL Ratio, Triglycerides/HDL Ratio, S.Cholestrol/HDL Ratio
           (VLDL and LDL are renamed + kept; ratios are new calculated params)
"""

from django.core.management.base import BaseCommand
from lab.models import Test, TestParameter


class Command(BaseCommand):
    help = 'Fix KFT / LFT / Lipid test parameters to match updated standard'

    def handle(self, *args, **options):
        self.fix_kft()
        self.fix_lft()
        self.fix_lipid()
        self.stdout.write(self.style.SUCCESS('\n✅ All test parameters updated successfully!'))
        self.stdout.write('   New bookings will use updated parameters.')
        self.stdout.write('   Existing report entries are NOT changed (values already saved).')

    # ---------------------------------------------
    def fix_kft(self):
        self.stdout.write('\n-- KFT --')
        test = self._get_test(['Kidney Function Test (KFT)', 'KFT', 'Kidney Function Test'])
        if not test:
            return

        # Remove Sodium, Potassium, Chloride
        to_remove = ['sodium', 'potassium', 'chloride', 'na+', 'k+', 'cl-', 'phosphorus']
        removed = 0
        for p in TestParameter.objects.filter(test=test):
            if any(r in p.param_name.lower() for r in to_remove):
                self.stdout.write(f'  Removing: {p.param_name}')
                p.delete()
                removed += 1
        self.stdout.write(f'  Removed {removed} parameters')

        # Add BUN after Uric Acid (sort_order = 4)
        if not TestParameter.objects.filter(test=test, param_name__iexact='BUN').exists():
            # Shift Calcium and Phosphorus down
            for p in TestParameter.objects.filter(test=test, sort_order__gte=4):
                p.sort_order += 1
                p.save()
            TestParameter.objects.create(
                test=test,
                param_name='BUN',
                unit='mg/dL',
                lower_limit=7.0,
                upper_limit=20.0,
                is_text=False,
                sort_order=4,
            )
            self.stdout.write(self.style.SUCCESS('  Added: BUN (mg/dL, 7-20)'))
        else:
            self.stdout.write('  BUN already exists, skipping')

        self._print_params(test)

    # ---------------------------------------------
    def fix_lft(self):
        self.stdout.write('\n-- LFT --')
        test = self._get_test(['Liver Function Test (LFT)', 'LFT', 'Liver Function Test'])
        if not test:
            return

        # Remove GGT
        removed = 0
        for p in TestParameter.objects.filter(test=test):
            if 'ggt' in p.param_name.lower() or 'gamma' in p.param_name.lower():
                self.stdout.write(f'  Removing: {p.param_name}')
                p.delete()
                removed += 1

        if removed == 0:
            self.stdout.write('  GGT not found (may already be removed)')
        else:
            self.stdout.write(f'  Removed {removed} GGT parameter(s)')

        self._print_params(test)

    # ---------------------------------------------
    def fix_lipid(self):
        self.stdout.write('\n-- Lipid Profile --')
        test = self._get_test(['Lipid Profile Test', 'Lipid Profile', 'Lipid'])
        if not test:
            return

        # Rename map: old name (lowercase match) -> new standard name
        rename_map = {
            'total cholesterol':             ('S.Cholestrol Total',                 0,   200,  1),
            'triglycerides':                 ('Triglycerides - Serum',              0,   150,  2),
            'hdl cholesterol':               ('Cholesterol - HDL (Direct)',         35,  80,   3),
            'vldl cholesterol':              ('VLDL -Very Low Density Lipoprotein', 16,  43,   4),
            'ldl cholesterol (bad)':         ('LDL Cholestrol',                     30,  100,  5),
            'ldl cholesterol':               ('LDL Cholestrol',                     30,  100,  5),
        }

        for p in TestParameter.objects.filter(test=test):
            key = p.param_name.strip().lower()
            if key in rename_map:
                new_name, lo, hi, order = rename_map[key]
                old_name = p.param_name
                p.param_name = new_name
                p.lower_limit = lo
                p.upper_limit = hi
                p.sort_order = order
                p.save()
                self.stdout.write(f'  Renamed: "{old_name}" -> "{new_name}"')

        # Add calculated ratio params if not present
        new_params = [
            {'n': 'LDL Cholestrol/HDL Ratio',   'u': '', 'lo': 0, 'hi': 4.0,  'order': 6},
            {'n': 'Triglycerides/HDL Ratio',     'u': '', 'lo': 0, 'hi': 5.9,  'order': 7},
            {'n': 'S.Cholestrol/HDL Ratio',      'u': '', 'lo': 0, 'hi': 4.0,  'order': 8},
        ]
        for p in new_params:
            exists = TestParameter.objects.filter(
                test=test, param_name__iexact=p['n']
            ).exists()
            if not exists:
                TestParameter.objects.create(
                    test=test,
                    param_name=p['n'],
                    unit=p['u'],
                    lower_limit=p['lo'],
                    upper_limit=p['hi'],
                    is_text=False,
                    sort_order=p['order'],
                )
                self.stdout.write(self.style.SUCCESS(f"  Added: {p['n']}"))
            else:
                self.stdout.write(f"  Already exists: {p['n']}")

        self._print_params(test)

    # ---------------------------------------------
    def _get_test(self, names):
        for name in names:
            try:
                t = Test.objects.get(name__iexact=name)
                self.stdout.write(f'  Found test: "{t.name}" (id={t.pk})')
                return t
            except Test.DoesNotExist:
                continue
        # Try partial match
        for name in names:
            qs = Test.objects.filter(name__icontains=name.split()[0])
            if qs.exists():
                t = qs.first()
                self.stdout.write(f'  Found test (partial): "{t.name}" (id={t.pk})')
                return t
        self.stdout.write(self.style.WARNING(f'  ⚠ Test not found for: {names}'))
        return None

    def _print_params(self, test):
        params = TestParameter.objects.filter(test=test).order_by('sort_order')
        self.stdout.write(f'  Final params ({params.count()}):')
        for p in params:
            self.stdout.write(f'    {p.sort_order}. {p.param_name} [{p.unit}] {p.lower_limit}-{p.upper_limit}')
