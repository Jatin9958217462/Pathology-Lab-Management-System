"""
AI / ML Diagnostic Interpretation Engine
==========================================
Stage 1 (current): Rule-based engine -- flags abnormal parameters,
generates structured clinical commentary in Hindi + English.

Stage 2 (upgrade path): OpenAI GPT-4 / local LLM integration
for natural language clinical interpretation.

Usage:
  from lab.ai_interpretation import generate_interpretation
  ai = generate_interpretation(report)
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Clinical significance rules per test category
CATEGORY_CONTEXT = {
    'Haematology': 'Blood count analysis',
    'Biochemistry': 'Biochemical markers',
    'Serology': 'Serological markers',
    'Hormones': 'Hormonal profile',
    'Clinical Pathology': 'Clinical pathology findings',
    'Histopathology': 'Histopathology findings',
}

SEVERITY_THRESHOLDS = {
    'critical': 3,    # 3+ critical flags
    'moderate': 2,    # 2+ high/low flags
    'mild': 1,        # 1 abnormal
    'normal': 0,
}

# Well-known parameter interpretation hints
PARAM_HINTS = {
    'hemoglobin': {
        'low': 'Anemia ka indication. Iron, Vitamin B12 ya folic acid deficiency ho sakta hai.',
        'high': 'Polycythemia ya dehydration ka indication.',
    },
    'wbc': {
        'low': 'Leukopenia -- immune system ki kamzori ya viral infection.',
        'high': 'Infection, inflammation ya blood disorder ka indication.',
    },
    'platelets': {
        'low': 'Thrombocytopenia -- bleeding risk badh sakta hai.',
        'high': 'Thrombocytosis -- clotting risk ya reactive condition.',
    },
    'glucose': {
        'high': 'Hyperglycemia -- diabetes ka indication. Doctor se milein.',
        'low': 'Hypoglycemia -- turant glucose intake zaruri.',
    },
    'creatinine': {
        'high': 'Kidney function mein gadbadi ho sakti hai.',
    },
    'urea': {
        'high': 'Elevated BUN -- kidney function ya dehydration check karein.',
    },
    'tsh': {
        'high': 'Hypothyroidism ka indication. Thyroid function check karein.',
        'low': 'Hyperthyroidism ya suppressed TSH.',
    },
    'sgpt': {'high': 'Liver mein inflammation ya damage ka indication (ALT).'},
    'sgot': {'high': 'Liver ya cardiac stress ka indication (AST).'},
    'bilirubin': {'high': 'Jaundice ya liver/bile duct issue.'},
    'cholesterol': {'high': 'Hypercholesterolemia -- cardiovascular risk factor.'},
}


def _match_hint(param_name: str, flag: str) -> str:
    """Match parameter name to hint dictionary (case-insensitive partial match)."""
    pname = param_name.lower().replace(' ', '')
    for key, hints in PARAM_HINTS.items():
        if key in pname:
            return hints.get(flag, '')
    return ''


def generate_interpretation(report) -> 'AIInterpretation':
    """
    Generate rule-based AI interpretation for a report.
    Creates/updates AIInterpretation record and returns it.
    """
    from .models import AIInterpretation

    results = list(report.results.all())
    if not results:
        ai, _ = AIInterpretation.objects.update_or_create(
            report=report,
            defaults={
                'interpretation': 'Koi parameter results nahi mile.',
                'flags_summary': '',
                'severity': 'normal',
                'status': 'generated',
                'model_used': 'rule-based-v1',
            }
        )
        return ai

    # Collect abnormal parameters
    high_params    = []
    low_params     = []
    critical_params= []
    normal_count   = 0

    for r in results:
        if r.flag == 'high':
            high_params.append(r)
        elif r.flag == 'low':
            low_params.append(r)
        elif r.flag == 'critical':
            critical_params.append(r)
        else:
            normal_count += 1

    total_abnormal = len(high_params) + len(low_params) + len(critical_params)

    # Determine severity
    if critical_params:
        severity = 'critical'
    elif total_abnormal >= SEVERITY_THRESHOLDS['moderate']:
        severity = 'moderate'
    elif total_abnormal >= SEVERITY_THRESHOLDS['mild']:
        severity = 'mild'
    else:
        severity = 'normal'

    # Build flags summary
    flag_lines = []
    for r in critical_params:
        flag_lines.append(f"⚠️ CRITICAL -- {r.param_name}: {r.value} {r.unit} (range: {r.normal_range})")
    for r in high_params:
        flag_lines.append(f"↑ HIGH -- {r.param_name}: {r.value} {r.unit} (range: {r.normal_range})")
    for r in low_params:
        flag_lines.append(f"↓ LOW -- {r.param_name}: {r.value} {r.unit} (range: {r.normal_range})")

    flags_summary = "\n".join(flag_lines) if flag_lines else "Sab parameters normal range mein hain."

    # Build interpretation text
    test_name     = report.test.display_name
    category      = report.test.category
    patient       = report.booking.patient
    context_line  = CATEGORY_CONTEXT.get(category, '')

    lines = [
        f"Test: {test_name} ({context_line})",
        f"Patient: {patient.full_name}, {patient.age} {patient.age_unit}, {patient.gender}",
        "",
    ]

    if severity == 'normal':
        lines.append("✅ Sab parameters normal range mein hain. Koi significant abnormality detect nahi hui.")
    else:
        lines.append(f"📋 {total_abnormal} abnormal parameter(s) detected:")
        lines.append("")
        for r in critical_params + high_params + low_params:
            hint = _match_hint(r.param_name, r.flag)
            lines.append(f"- {r.param_name}: {r.value} {r.unit}")
            if hint:
                lines.append(f"  -> {hint}")

    lines += [
        "",
        "-" * 40,
        "Note: Ye interpretation automated rule-based analysis hai.",
        "Final diagnosis ke liye doctor se consult karein.",
        "This report is for physician reference only.",
    ]

    interpretation_text = "\n".join(lines)

    ai, _ = AIInterpretation.objects.update_or_create(
        report=report,
        defaults={
            'interpretation': interpretation_text,
            'flags_summary': flags_summary,
            'severity': severity,
            'status': 'generated',
            'model_used': 'rule-based-v1',
        }
    )
    return ai


# --- Optional: OpenAI GPT upgrade path ----------------------------------------

def generate_interpretation_gpt(report, openai_api_key: str) -> str:
    """
    Stage 2 upgrade: use OpenAI GPT-4 for natural language interpretation.
    Call this instead of generate_interpretation() when OpenAI key is configured.
    Returns interpretation text string.
    """
    try:
        import openai
    except ImportError:
        return "OpenAI not installed. Run: pip install openai"

    openai.api_key = openai_api_key
    results = list(report.results.all())
    results_text = "\n".join(
        f"{r.param_name}: {r.value} {r.unit} (normal: {r.normal_range}) [{r.flag}]"
        for r in results
    )

    prompt = f"""You are an experienced clinical pathologist in India.
Analyze these lab results and provide a brief clinical interpretation in simple language.
Mention any concerning values, possible causes, and whether the doctor should be consulted urgently.

Test: {report.test.display_name}
Patient: {report.booking.patient.full_name}, Age: {report.booking.patient.age} {report.booking.patient.age_unit}

Results:
{results_text}

Provide interpretation in 3-4 sentences. End with: "Please consult your doctor for final diagnosis."
"""

    try:
        client   = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return f"AI interpretation failed: {e}"
