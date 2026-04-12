"""
Lab Analyser Machine Interface
================================
Handles auto-import of results from lab analysers via:
  - ASTM E1394 (most common -- Sysmex, Mindray, Beckman)
  - CSV/TXT file upload (Erba, Transasia, etc.)
  - TCP socket polling

Typical flow:
  1. Machine sends ASTM message to TCP port (e.g. 4000)
  2. analyser_tcp_listener() receives raw ASTM data
  3. parse_astm_message() extracts sample ID + results
  4. import_to_report() matches Sample ID to Booking and creates ReportResults

Setup:
  - Configure AnalyserInterface in admin with IP, port, protocol
  - Add test_mapping JSON: {"WBC": 5, "HGB": 3}  (machine code -> TestParameter pk)
  - Run management command: python manage.py run_analyser_listener
"""
import json
import logging
import re
import socket
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

# ASTM control characters
STX = b'\x02'
ETX = b'\x03'
EOT = b'\x04'
ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'
ETB = b'\x17'
CR  = b'\r'
LF  = b'\n'


# --- ASTM Parser -------------------------------------------------------------

def parse_astm_message(raw: str) -> dict:
    """
    Parse ASTM E1394 message into a structured dict.
    Returns: {'sample_id': str, 'results': [{'code': str, 'value': str, 'unit': str, 'flag': str}]}
    """
    sample_id = ""
    results   = []

    for line in raw.replace('\r', '\n').split('\n'):
        line = line.strip()
        if not line:
            continue

        parts = line.split('|')
        rec_type = parts[0][-1] if parts[0] else ''

        if rec_type == 'S':   # Sample record
            sample_id = parts[3] if len(parts) > 3 else ""
            sample_id = sample_id.strip('^').strip()

        elif rec_type == 'R':  # Result record
            if len(parts) < 6:
                continue
            test_code = parts[2].split('^')[0].strip() if parts[2] else ''
            value     = parts[3].strip() if len(parts) > 3 else ''
            unit      = parts[4].strip() if len(parts) > 4 else ''
            ref_range = parts[5].strip() if len(parts) > 5 else ''
            flag      = parts[6].strip() if len(parts) > 6 else ''
            if test_code and value:
                results.append({
                    'code': test_code,
                    'value': value,
                    'unit': unit,
                    'ref_range': ref_range,
                    'flag': flag,
                })

    return {'sample_id': sample_id, 'results': results}


def parse_csv_result(content: str, header_mapping: dict = None) -> dict:
    """
    Parse CSV/TXT file from analyser.
    header_mapping: {'SampleID': 0, 'WBC': 1, 'HGB': 2, ...}
    Returns same structure as parse_astm_message.
    """
    lines = content.strip().split('\n')
    if not lines:
        return {'sample_id': '', 'results': []}

    headers = [h.strip() for h in lines[0].split(',')]
    results = []
    sample_id = ""

    for line in lines[1:]:
        if not line.strip():
            continue
        vals = [v.strip() for v in line.split(',')]
        row  = dict(zip(headers, vals))

        if not sample_id:
            sample_id = row.get('SampleID', row.get('Sample ID', row.get('SAMPLE_ID', '')))

        for col, value in row.items():
            if col.lower() in ('sampleid', 'sample id', 'sample_id', 'barcode'):
                continue
            if value and col:
                results.append({'code': col, 'value': value, 'unit': '', 'ref_range': '', 'flag': ''})

    return {'sample_id': sample_id, 'results': results}


# --- Import to Report ---------------------------------------------------------

def import_analyser_result(analyser_result_pk: int) -> dict:
    """
    Try to match AnalyserResult to a Booking/Report and import results.
    Returns {'success': bool, 'report_id': str, 'imported': int, 'errors': list}
    """
    from .models import AnalyserResult, Booking, Report, ReportResult, TestParameter

    try:
        ar = AnalyserResult.objects.select_related('analyser').get(pk=analyser_result_pk)
    except AnalyserResult.DoesNotExist:
        return {'success': False, 'report_id': '', 'imported': 0, 'errors': ['AnalyserResult not found']}

    parsed  = json.loads(ar.parsed_json) if ar.parsed_json else parse_astm_message(ar.raw_data)
    sample  = parsed.get('sample_id', '').strip()
    results = parsed.get('results', [])
    errors  = []

    if not sample:
        ar.status = 'error'; ar.error_detail = 'No sample ID in message'; ar.save()
        return {'success': False, 'report_id': '', 'imported': 0, 'errors': ['No sample ID']}

    # Try to find booking by receipt_id or patient_id
    booking = None
    for model_filter in [
        {'receipt_id__icontains': sample},
        {'patient__patient_id__icontains': sample},
        {'patient__custom_display_id__icontains': sample},
    ]:
        try:
            booking = Booking.objects.get(**model_filter)
            break
        except (Booking.DoesNotExist, Booking.MultipleObjectsReturned):
            continue

    if not booking:
        ar.status = 'error'; ar.error_detail = f'Booking not found for sample: {sample}'; ar.save()
        return {'success': False, 'report_id': '', 'imported': 0, 'errors': [f'Booking not found: {sample}']}

    # Load test mapping from analyser config
    mapping = {}
    if ar.analyser and ar.analyser.test_mapping:
        try:
            mapping = json.loads(ar.analyser.test_mapping)  # {"WBC": param_pk}
        except Exception:
            pass

    # Find or pick first pending report for this booking
    report = booking.reports.first()
    if not report:
        ar.status = 'error'; ar.error_detail = 'No reports found for booking'; ar.save()
        return {'success': False, 'report_id': '', 'imported': 0, 'errors': ['No report for booking']}

    imported = 0
    for res in results:
        code  = res['code']
        value = res['value']
        param_pk = mapping.get(code)
        param    = None

        if param_pk:
            try:
                param = TestParameter.objects.get(pk=param_pk)
            except TestParameter.DoesNotExist:
                pass

        if not param:
            # Try by name match in test parameters
            param = TestParameter.objects.filter(
                test=report.test, param_name__iexact=code
            ).first()

        if param:
            rr, created = ReportResult.objects.update_or_create(
                report=report, parameter=param,
                defaults={
                    'param_name': param.param_name,
                    'value': value,
                    'unit': res.get('unit', param.unit),
                    'lower_limit': param.lower_limit,
                    'upper_limit': param.upper_limit,
                    'sort_order': param.sort_order,
                }
            )
            rr.flag = rr.compute_flag(); rr.save()
            imported += 1
        else:
            errors.append(f"No mapping for code: {code}")

    ar.status = 'imported'; ar.linked_report = report; ar.save()
    return {'success': True, 'report_id': report.report_id, 'imported': imported, 'errors': errors}


# --- TCP Listener (run as background thread / management command) -----------

class ASTMTCPListener:
    """
    Background TCP server that listens for ASTM messages from analysers.
    Run via management command: python manage.py run_analyser_listener
    """
    def __init__(self, host: str = '0.0.0.0', port: int = 4000, analyser_pk: int = None):
        self.host        = host
        self.port        = port
        self.analyser_pk = analyser_pk
        self._stop       = threading.Event()

    def handle_client(self, conn, addr):
        logger.info("Analyser connected from %s", addr)
        data = b""
        try:
            conn.sendall(ENQ)  # Send ENQ to invite transmission
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if EOT in data:
                    break
            raw = data.decode('ascii', errors='replace')
            self._save_result(raw)
            conn.sendall(ACK)
        except Exception as e:
            logger.error("ASTM client error from %s: %s", addr, e)
        finally:
            conn.close()

    def _save_result(self, raw: str):
        from .models import AnalyserInterface, AnalyserResult
        parsed = parse_astm_message(raw)
        analyser = None
        if self.analyser_pk:
            try:
                analyser = AnalyserInterface.objects.get(pk=self.analyser_pk)
            except AnalyserInterface.DoesNotExist:
                pass

        ar = AnalyserResult.objects.create(
            analyser=analyser,
            sample_id=parsed.get('sample_id', 'UNKNOWN'),
            raw_data=raw,
            parsed_json=json.dumps(parsed),
            status='pending',
        )
        # Auto-import
        try:
            import_analyser_result(ar.pk)
        except Exception as e:
            logger.error("Auto-import error: %s", e)

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        server.settimeout(1.0)
        logger.info("ASTM listener started on %s:%d", self.host, self.port)
        while not self._stop.is_set():
            try:
                conn, addr = server.accept()
                t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
        server.close()
        logger.info("ASTM listener stopped")

    def stop(self):
        self._stop.set()
