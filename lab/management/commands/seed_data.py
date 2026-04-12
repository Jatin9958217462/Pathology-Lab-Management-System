from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from lab.models import UserProfile, Test, TestParameter


RATE_LIST = [
    # -- HAEMATOLOGY ----------------------------------------------------------
    {'name':'HB', 'cat':'Haematology', 'price':50,  'sample':'Blood (EDTA)', 'tat':'1 Hr'},
    {'name':'TLC','cat':'Haematology', 'price':50,  'sample':'Blood (EDTA)', 'tat':'1 Hr'},
    {'name':'DLC','cat':'Haematology', 'price':50,  'sample':'Blood (EDTA)', 'tat':'1 Hr'},
    {'name':'ESR','cat':'Haematology', 'price':50,  'sample':'Blood (EDTA)', 'tat':'1 Hr'},
    {'name':'HB, TLC, DLC, ESR (Haemogram)','cat':'Haematology','price':100,'sample':'Blood (EDTA)','tat':'2 Hr'},
    {'name':'PCV','cat':'Haematology', 'price':80,  'sample':'Blood (EDTA)', 'tat':'1 Hr'},
    {'name':'Peripheral Smear','cat':'Haematology','price':100,'sample':'Blood (EDTA)','tat':'2 Hr'},
    {'name':'P.S. For M.P.','cat':'Haematology','price':80,'sample':'Blood (EDTA)','tat':'1 Hr'},
    {'name':'P.S. For Microfilaria','cat':'Haematology','price':1200,'sample':'Blood (EDTA)','tat':'4 Hr'},
    {'name':'AEC (Abs Eosinophil Count)','cat':'Haematology','price':100,'sample':'Blood (EDTA)','tat':'2 Hr'},
    {'name':'Platelets Count','cat':'Haematology','price':100,'sample':'Blood (EDTA)','tat':'1 Hr'},
    {'name':'B.T. (Bleeding Time)','cat':'Haematology','price':100,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'C.T. (Clotting Time)','cat':'Haematology','price':100,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'Reticulocyte Count','cat':'Haematology','price':200,'sample':'Blood (EDTA)','tat':'2 Hr'},
    {'name':'Total RBC','cat':'Haematology','price':60,'sample':'Blood (EDTA)','tat':'1 Hr'},
    {'name':'Blood Group (ABO) Rh','cat':'Haematology','price':100,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'CBC (Complete Haemogram)','cat':'Haematology','price':300,'sample':'Blood (EDTA)','tat':'2 Hr'},
    {'name':'Malaria Antigen','cat':'Haematology','price':350,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'P.T. & INR','cat':'Haematology','price':400,'sample':'Sodium Citrate','tat':'2 Hr'},
    # -- SEROLOGY -------------------------------------------------------------
    {'name':'Typhi Dot IgM','cat':'Serology','price':400,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'VDRL','cat':'Serology','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Widal Test','cat':'Serology','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'R.A. Factor','cat':'Serology','price':200,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'HBsAg (Hepatitis B Virus)','cat':'Serology','price':200,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'HIV 1 & 2','cat':'Serology','price':350,'sample':'Blood (Plain)','tat':'1 Hr'},
    {'name':'Anti Streptolysin O (ASO)','cat':'Serology','price':500,'sample':'Blood (Plain)','tat':'3 Hr'},
    {'name':'C-Reactive Protein (CRP)','cat':'Serology','price':200,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'HCV (Hepatitis C Virus)','cat':'Serology','price':500,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Chikungunya Serology','cat':'Serology','price':800,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Dengue Serology NS1','cat':'Serology','price':600,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'CRP Quantitative','cat':'Serology','price':400,'sample':'Blood (Plain)','tat':'3 Hr'},
    # -- BIO-CHEMICAL ---------------------------------------------------------
    {'name':'Blood Sugar F/PP/R (Each)','cat':'Biochemistry','price':50,'sample':'Floride','tat':'1 Hr'},
    {'name':'GTT','cat':'Biochemistry','price':150,'sample':'Floride','tat':'3 Hr'},
    {'name':'Blood Urea','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Uric Acid','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Creatinine','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Bilirubin (T, D, IN)','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Alka-Phosphatase','cat':'Biochemistry','price':150,'sample':'Blood (Plain)','tat':'3 Hr'},
    {'name':'SGOT/AST','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'SGPT/ALT','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Albumin','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'T. Protein','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Triglyceride','cat':'Biochemistry','price':150,'sample':'Blood (Plain)','tat':'3 Hr'},
    {'name':'Cholesterol','cat':'Biochemistry','price':150,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'HDL-Cholesterol','cat':'Biochemistry','price':250,'sample':'Blood (Plain)','tat':'3 Hr'},
    {'name':'C.P.K. / CPK-MB','cat':'Biochemistry','price':500,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'L.D.H.','cat':'Biochemistry','price':600,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'S. Iron / TIBC','cat':'Biochemistry','price':600,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Liver Function Test (LFT)','cat':'Biochemistry','price':400,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Kidney Function Test (KFT)','cat':'Biochemistry','price':500,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Lipid Profile Test','cat':'Biochemistry','price':500,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Electrolytes (Na, K, CL)','cat':'Biochemistry','price':300,'sample':'Blood (Plain)','tat':'3 Hr'},
    {'name':'Sodium','cat':'Biochemistry','price':150,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Potassium','cat':'Biochemistry','price':150,'sample':'Blood (Plain)','tat':'2 Hr'},
    {'name':'Calcium / Phosphorus','cat':'Biochemistry','price':100,'sample':'Blood (Plain)','tat':'2 Hr'},
    # -- CLINICAL PATHOLOGY ---------------------------------------------------
    {'name':'Urine R/M','cat':'Clinical Pathology','price':100,'sample':'Urine','tat':'1 Hr'},
    {'name':'Urine Bile Salt','cat':'Clinical Pathology','price':100,'sample':'Urine','tat':'1 Hr'},
    {'name':'Urine Bilepigment','cat':'Clinical Pathology','price':100,'sample':'Urine','tat':'1 Hr'},
    {'name':'Urine 24 Hr Protein','cat':'Clinical Pathology','price':600,'sample':'Urine','tat':'4 Hr'},
    {'name':'Urine Pregnancy Test (ELISA)','cat':'Clinical Pathology','price':100,'sample':'Urine','tat':'30 Min'},
    {'name':'Urine Culture/Sensitivity','cat':'Clinical Pathology','price':300,'sample':'Urine','tat':'48 Hr'},
    {'name':'Stool for Occult Blood','cat':'Clinical Pathology','price':200,'sample':'Stool','tat':'2 Hr'},
    {'name':'Stool R/M','cat':'Clinical Pathology','price':100,'sample':'Stool','tat':'1 Hr'},
    {'name':'Stool/Pus/Sputum C/S','cat':'Clinical Pathology','price':300,'sample':'Stool','tat':'48 Hr'},
    {'name':'Sputum for AFB','cat':'Clinical Pathology','price':100,'sample':'Sputum','tat':'4 Hr'},
    {'name':'Semen Analysis','cat':'Clinical Pathology','price':200,'sample':'Semen','tat':'2 Hr'},
    # -- HISTO/CYTOLOGY -------------------------------------------------------
    {'name':'F.N.A.C. (Lab)','cat':'Histopathology','price':800,'sample':'Tissue','tat':'3 Days'},
    {'name':'Biopsy Large Specimen','cat':'Histopathology','price':1200,'sample':'Tissue','tat':'5 Days'},
    # -- HORMONES -------------------------------------------------------------
    {'name':'T3','cat':'Hormones','price':250,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'T4','cat':'Hormones','price':250,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'TSH','cat':'Hormones','price':250,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'T3, T4, TSH (Thyroid Profile)','cat':'Hormones','price':500,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'LH','cat':'Hormones','price':450,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'FSH','cat':'Hormones','price':450,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Prolactin','cat':'Hormones','price':450,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'Testosterone','cat':'Hormones','price':600,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'PSA Total','cat':'Hormones','price':600,'sample':'Blood (Plain)','tat':'4 Hr'},
    {'name':'TORCH IgG','cat':'Hormones','price':1200,'sample':'Blood (Plain)','tat':'1 Day'},
    {'name':'TORCH IgM','cat':'Hormones','price':1200,'sample':'Blood (Plain)','tat':'1 Day'},
    {'name':'T.B. Gold','cat':'Hormones','price':2500,'sample':'Heparin','tat':'1 Day'},
    {'name':'T.B. PCR','cat':'Hormones','price':2000,'sample':'Blood (EDTA)','tat':'2 Days'},
]

# CBC parameters (from image 5 & 6)
CBC_PARAMS = [
    {'n':'Hemoglobin',             'u':'g/dl',       'lo':11.5, 'hi':16,    'is_text':False, 'order':1},
    {'n':'Total Leukocyte Count',  'u':'/cumm',      'lo':4000, 'hi':11000, 'is_text':False, 'order':2},
    {'n':'Differential Leukocyte Count','u':'',      'lo':None, 'hi':None,  'is_text':True,  'order':3},
    {'n':'Neutrophils',            'u':'%',          'lo':40,   'hi':70,    'is_text':False, 'order':4},
    {'n':'Lymphocytes',            'u':'%',          'lo':20,   'hi':45,    'is_text':False, 'order':5},
    {'n':'Eosinophils',            'u':'%',          'lo':1,    'hi':6,     'is_text':False, 'order':6},
    {'n':'Monocytes',              'u':'%',          'lo':2,    'hi':10,    'is_text':False, 'order':7},
    {'n':'Basophil',               'u':'%',          'lo':0,    'hi':1,     'is_text':False, 'order':8},
    {'n':'RBC Count',              'u':'/mm3',       'lo':4.5,  'hi':5.8,   'is_text':False, 'order':9},
    {'n':'PCV',                    'u':'%',          'lo':37,   'hi':47,    'is_text':False, 'order':10},
    {'n':'MCV',                    'u':'femtoliter', 'lo':76,   'hi':96,    'is_text':False, 'order':11},
    {'n':'MCH (Calculated)',       'u':'picogram',   'lo':27,   'hi':32,    'is_text':False, 'order':12},
    {'n':'MCHC (Calculated)',      'u':'gm/dl',      'lo':31,   'hi':35,    'is_text':False, 'order':13},
    {'n':'Platelet Count',         'u':'lacs/cumm',  'lo':1.5,  'hi':4.5,   'is_text':False, 'order':14},
    {'n':'ESR (Wintrobe)',         'u':'1 hr',       'lo':0,    'hi':20,    'is_text':False, 'order':15},
]

LFT_PARAMS = [
    {'n':'Total Bilirubin',             'u':'mg/dL','lo':0.2, 'hi':1.2, 'order':1},
    {'n':'Direct Bilirubin',            'u':'mg/dL','lo':0.0, 'hi':0.3, 'order':2},
    {'n':'Indirect Bilirubin',          'u':'mg/dL','lo':0.2, 'hi':0.9, 'order':3},
    {'n':'SGPT (ALT)',                  'u':'U/L',  'lo':7,   'hi':56,  'order':4},
    {'n':'SGOT (AST)',                  'u':'U/L',  'lo':10,  'hi':40,  'order':5},
    {'n':'Alkaline Phosphatase (ALP)',  'u':'U/L',  'lo':44,  'hi':147, 'order':6},
    {'n':'Total Protein',               'u':'g/dL', 'lo':6.0, 'hi':8.3, 'order':7},
    {'n':'Albumin',                     'u':'g/dL', 'lo':3.5, 'hi':5.0, 'order':8},
    {'n':'Globulin',                    'u':'g/dL', 'lo':2.0, 'hi':3.5, 'order':9},
    {'n':'A:G Ratio',                   'u':'',     'lo':1.0, 'hi':2.5, 'order':10},
]

KFT_PARAMS = [
    {'n':'Blood Urea',      'u':'mg/dL', 'lo':17,  'hi':43,   'order':1},
    {'n':'Creatinine',      'u':'mg/dL', 'lo':0.7, 'hi':1.3,  'order':2},
    {'n':'Uric Acid',       'u':'mg/dL', 'lo':3.5, 'hi':7.2,  'order':3},
    {'n':'BUN',             'u':'mg/dL', 'lo':7,   'hi':20,   'order':4},
    {'n':'Calcium',         'u':'mg/dL', 'lo':8.5, 'hi':10.5, 'order':5},
]

THYROID_PARAMS = [
    {'n':'T3 (Total Triiodothyronine)','u':'ng/dL',  'lo':80,  'hi':200, 'order':1},
    {'n':'T4 (Total Thyroxine)',        'u':'µg/dL',  'lo':5.0, 'hi':12.0,'order':2},
    {'n':'TSH',                         'u':'µIU/mL', 'lo':0.4, 'hi':4.0, 'order':3},
]

LIPID_PARAMS = [
    {'n':'S.Cholestrol Total',            'u':'mg/dL','lo':0,   'hi':200, 'order':1},
    {'n':'Triglycerides - Serum',         'u':'mg/dL','lo':0,   'hi':150, 'order':2},
    {'n':'Cholesterol - HDL (Direct)',    'u':'mg/dL','lo':35,  'hi':80,  'order':3},
    {'n':'VLDL -Very Low Density Lipoprotein','u':'mg/dL','lo':16,'hi':43,'order':4},
    {'n':'LDL Cholestrol',                'u':'mg/dL','lo':30,  'hi':100, 'order':5},
    {'n':'LDL Cholestrol/HDL Ratio',      'u':'',     'lo':0,   'hi':4,   'order':6},
    {'n':'Triglycerides/HDL Ratio',       'u':'',     'lo':0,   'hi':5.9, 'order':7},
    {'n':'S.Cholestrol/HDL Ratio',        'u':'',     'lo':0,   'hi':4,   'order':8},
]

WIDAL_PARAMS = [
    {'n':'S. Typhi O Antigen',   'u':'','lo':None,'hi':None,'is_text':True,'order':1},
    {'n':'S. Typhi H Antigen',   'u':'','lo':None,'hi':None,'is_text':True,'order':2},
    {'n':'S. Paratyphi AO',      'u':'','lo':None,'hi':None,'is_text':True,'order':3},
    {'n':'S. Paratyphi AH',      'u':'','lo':None,'hi':None,'is_text':True,'order':4},
]

URINE_PARAMS = [
    {'n':'Colour',             'u':'','lo':None,'hi':None,'is_text':True,'order':1},
    {'n':'Appearance',         'u':'','lo':None,'hi':None,'is_text':True,'order':2},
    {'n':'pH',                 'u':'','lo':4.5,'hi':8.0,'order':3},
    {'n':'Specific Gravity',   'u':'','lo':1.001,'hi':1.030,'order':4},
    {'n':'Protein',            'u':'','lo':None,'hi':None,'is_text':True,'order':5},
    {'n':'Glucose',            'u':'','lo':None,'hi':None,'is_text':True,'order':6},
    {'n':'Ketones',            'u':'','lo':None,'hi':None,'is_text':True,'order':7},
    {'n':'Bilirubin',          'u':'','lo':None,'hi':None,'is_text':True,'order':8},
    {'n':'Blood/Haemoglobin',  'u':'','lo':None,'hi':None,'is_text':True,'order':9},
    {'n':'Nitrite',            'u':'','lo':None,'hi':None,'is_text':True,'order':10},
    {'n':'Pus Cells (WBC)',    'u':'/HPF','lo':0,'hi':5,'order':11},
    {'n':'RBC',                'u':'/HPF','lo':0,'hi':2,'order':12},
    {'n':'Epithelial Cells',   'u':'/HPF','lo':0,'hi':5,'order':13},
    {'n':'Casts',              'u':'','lo':None,'hi':None,'is_text':True,'order':14},
    {'n':'Crystals',           'u':'','lo':None,'hi':None,'is_text':True,'order':15},
    {'n':'Bacteria',           'u':'','lo':None,'hi':None,'is_text':True,'order':16},
]

MALARIA_PARAMS = [
    {'n':'P. Falciparum Antigen (HRP-2)','u':'','lo':None,'hi':None,'is_text':True,'order':1},
    {'n':'P. Vivax Antigen (pLDH)',       'u':'','lo':None,'hi':None,'is_text':True,'order':2},
]

DENGUE_PARAMS = [
    {'n':'Dengue NS1 Antigen','u':'','lo':None,'hi':None,'is_text':True,'order':1},
    {'n':'Dengue IgG',         'u':'','lo':None,'hi':None,'is_text':True,'order':2},
    {'n':'Dengue IgM',         'u':'','lo':None,'hi':None,'is_text':True,'order':3},
]

TEST_PARAM_MAP = {
    'HB, TLC, DLC, ESR (Haemogram)': CBC_PARAMS,
    'CBC (Complete Haemogram)': CBC_PARAMS,
    'Liver Function Test (LFT)': LFT_PARAMS,
    'Kidney Function Test (KFT)': KFT_PARAMS,
    'T3, T4, TSH (Thyroid Profile)': THYROID_PARAMS,
    'Lipid Profile Test': LIPID_PARAMS,
    'Widal Test': WIDAL_PARAMS,
    'Urine R/M': URINE_PARAMS,
    'Malaria Antigen': MALARIA_PARAMS,
    'Dengue Serology NS1': DENGUE_PARAMS,
    'HBsAg (Hepatitis B Virus)': [{'n':'HBsAg','u':'','lo':None,'hi':None,'is_text':True,'order':1}],
    'CRP Quantitative': [{'n':'CRP (Quantitative)','u':'mg/L','lo':0,'hi':6,'order':1}],
}


class Command(BaseCommand):
    help = 'Seed Indian Path-Lab with all tests, parameters, and demo users'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Indian Path-Lab Setup ==='))

        # Users
        for uname, pw, role, email in [
            ('admin',  'Admin@1234',  'admin',  'admin@ipl.com'),
            ('staff',  'Staff@1234',  'staff',  'staff@ipl.com'),
            ('doctor', 'Doctor@1234', 'doctor', 'doctor@ipl.com'),
        ]:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, email, pw)
                if role == 'admin': u.is_staff = u.is_superuser = True; u.save()
                from lab.models import UserProfile
                UserProfile.objects.get_or_create(user=u, defaults={'role': role})
                self.stdout.write(self.style.SUCCESS(f'  OK User: {uname} / {pw}'))

        # Tests
        created = 0
        for item in RATE_LIST:
            t, c = Test.objects.get_or_create(
                name=item['name'],
                defaults={
                    'category': item['cat'],
                    'price':    item['price'],
                    'sample':   item['sample'],
                    'tat':      item['tat'],
                    'active':   True,
                }
            )
            if c:
                created += 1
                # Seed parameters if known
                params = TEST_PARAM_MAP.get(item['name'], [])
                for p in params:
                    TestParameter.objects.get_or_create(
                        test=t, param_name=p['n'],
                        defaults={
                            'unit':        p.get('u',''),
                            'lower_limit': p.get('lo'),
                            'upper_limit': p.get('hi'),
                            'is_text':     p.get('is_text', False),
                            'sort_order':  p.get('order', 0),
                        }
                    )
        self.stdout.write(self.style.SUCCESS(f'  OK Tests seeded: {created} new'))
        self.stdout.write(self.style.SUCCESS('\n  Setup complete! Run: python manage.py runserver'))
