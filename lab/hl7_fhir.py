"""
HL7 / FHIR Integration Module
================================
Generates standard HL7 v2.x (ORU^R01) messages and FHIR R4 DiagnosticReport resources
from lab reports. Also handles sending to Hospital Information Systems (HIS).

HL7 ORU^R01 = Observation Result Unsolicited (lab result transmission)
FHIR        = Fast Healthcare Interoperability Resources (modern REST API standard)

Usage:
  from lab.hl7_fhir import generate_oru_r01, generate_fhir_diagnostic_report, send_to_his
  hl7_msg = generate_oru_r01(report)
  fhir_bundle = generate_fhir_diagnostic_report(report)
"""
import json
import logging
import datetime
import requests

logger = logging.getLogger(__name__)

HL7_DATETIME_FMT = "%Y%m%d%H%M%S"


def _hl7_escape(val: str) -> str:
    """Escape HL7 special characters."""
    return str(val).replace('\\', '\\E\\').replace('|', '\\F\\').replace('^', '\\S\\').replace('~', '\\R\\').replace('&', '\\T\\')


def generate_oru_r01(report) -> str:
    """
    Generate HL7 v2.5 ORU^R01 message for a finalized lab report.
    Returns the HL7 message string (pipe-delimited).
    """
    from .models import LabSettings
    s       = LabSettings.get()
    patient = report.booking.patient
    booking = report.booking
    now     = datetime.datetime.now().strftime(HL7_DATETIME_FMT)
    dob     = ""  # Patient DOB not stored; left blank
    lab_name = _hl7_escape(s.lab_name or "Indian Path-Lab")
    pid_name = f"{_hl7_escape(patient.last_name)}^{_hl7_escape(patient.first_name)}"

    lines = [
        # MSH -- Message Header
        f"MSH|^~\\&|{lab_name}|{lab_name}|HIS|HIS|{now}||ORU^R01^ORU_R01|{report.report_id}|P|2.5|||AL|NE|||UNICODE UTF-8",
        # PID -- Patient Identification
        f"PID|1||{patient.patient_id}^^^{lab_name}^PI||{pid_name}||{dob}|{patient.gender[:1].upper()}|||{_hl7_escape(patient.address)}||{patient.mobile}",
        # OBR -- Observation Request
        f"OBR|1|{booking.receipt_id}|{report.report_id}|{report.test.name}^{report.test.display_name}^^^L|||{report.sample_drawn_date or booking.sample_date}||||||||||||{report.report_date}|||F",
    ]

    # OBX -- Observation Result (one per parameter)
    for idx, result in enumerate(report.results.all(), start=1):
        obx_value = _hl7_escape(result.value)
        units     = _hl7_escape(result.unit)
        ref_range = f"{result.lower_limit}-{result.upper_limit}" if result.lower_limit is not None else ""
        flag_map  = {'high': 'H', 'low': 'L', 'critical': 'LL', 'normal': 'N', 'text': ''}
        flag      = flag_map.get(result.flag, 'N')
        lines.append(
            f"OBX|{idx}|NM|{_hl7_escape(result.param_name)}^^L||{obx_value}|{units}|{ref_range}|{flag}|||F"
        )

    lines.append("")   # trailing newline
    return "\r\n".join(lines)


def generate_fhir_diagnostic_report(report) -> dict:
    """
    Generate a FHIR R4 DiagnosticReport resource as a Python dict (serializable to JSON).
    """
    from .models import LabSettings
    s       = LabSettings.get()
    patient = report.booking.patient

    observations = []
    for idx, result in enumerate(report.results.all()):
        obs = {
            "resourceType": "Observation",
            "id": f"obs-{report.report_id}-{idx}",
            "status": "final",
            "code": {"text": result.param_name},
            "subject": {"reference": f"Patient/{patient.patient_id}"},
            "effectiveDateTime": str(report.report_date),
            "performer": [{"display": s.lab_name}],
        }
        try:
            numeric_val = float(result.value)
            obs["valueQuantity"] = {
                "value": numeric_val,
                "unit": result.unit,
                "system": "http://unitsofmeasure.org",
            }
            if result.lower_limit is not None and result.upper_limit is not None:
                obs["referenceRange"] = [{
                    "low":  {"value": result.lower_limit,  "unit": result.unit},
                    "high": {"value": result.upper_limit, "unit": result.unit},
                }]
            if result.flag in ('high', 'low', 'critical'):
                obs["interpretation"] = [{"text": result.get_flag_display()}]
        except (ValueError, TypeError):
            obs["valueString"] = result.value
        observations.append(obs)

    diagnostic_report = {
        "resourceType": "DiagnosticReport",
        "id": report.report_id,
        "status": "final" if report.is_finalized else "preliminary",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB", "display": "Laboratory"}]}],
        "code": {"text": report.test.display_name},
        "subject": {
            "reference": f"Patient/{patient.patient_id}",
            "display": patient.full_name,
        },
        "effectiveDateTime": str(report.report_date),
        "issued": report.created_at.isoformat() if report.created_at else None,
        "performer": [{"display": s.lab_name}],
        "result": [{"reference": f"#obs-{report.report_id}-{i}"} for i in range(len(observations))],
        "contained": observations,
        "conclusion": report.remarks or "",
    }

    bundle = {
        "resourceType": "Bundle",
        "type": "message",
        "entry": [{"resource": diagnostic_report}],
    }
    return bundle


def send_to_his(report, endpoint_url: str = None) -> dict:
    """
    Send HL7 ORU^R01 message to a HIS endpoint.
    endpoint_url comes from LabSettings.his_endpoint_url.
    Returns {'success': bool, 'status_code': int, 'response': str}
    """
    from .models import LabSettings, HL7FHIRLog
    s = LabSettings.get()
    url = endpoint_url or getattr(s, 'his_endpoint_url', '')

    if not url:
        return {'success': False, 'status_code': 0, 'response': 'HIS endpoint URL not configured'}

    hl7_msg = generate_oru_r01(report)

    log = HL7FHIRLog.objects.create(
        direction='outbound',
        msg_type='ORU_R01',
        patient=report.booking.patient,
        report=report,
        raw_message=hl7_msg,
        status='sent',
    )

    try:
        resp = requests.post(
            url, data=hl7_msg.encode('utf-8'),
            headers={'Content-Type': 'application/hl7-v2; charset=UTF-8'},
            timeout=15,
        )
        if resp.status_code in (200, 201, 204):
            log.status = 'ack'; log.save()
            return {'success': True, 'status_code': resp.status_code, 'response': resp.text[:500]}
        else:
            log.status = 'error'; log.error_detail = resp.text[:500]; log.save()
            return {'success': False, 'status_code': resp.status_code, 'response': resp.text[:500]}
    except Exception as e:
        log.status = 'error'; log.error_detail = str(e); log.save()
        logger.error("HIS send error: %s", e)
        return {'success': False, 'status_code': 0, 'response': str(e)}
