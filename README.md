# PathLab v1.1 — Laboratory Management System

A full-featured, web-based pathology laboratory management system built with Django.

## Version History

| Version | Date       | Changes |
|---------|------------|---------|
| v1.1    | 2026-04-09 | PDF header/footer system, Doctor portal, Auto-commission, QR bulk download, Search improvements, Professional comments |
| v1.0    | 2026-04-01 | Initial release |

## Features

### Core Lab Operations
- **Patient Management** — Registration, records, search, photo upload
- **Test Bookings** — Multi-test booking, payment tracking, bill PDF
- **Report Entry** — Parameter-wise entry with reference ranges and flags
- **Report PDF** — Letterhead header, footer, QR verification code
- **Bulk PDF / Print** — Multi-report export with per-page header/footer

### Doctor & Commission
- **Referring Doctors** — Master list with portal access linking
- **Doctor Portal** — Doctors login to see their patients' reports
- **Auto Commission** — Commission auto-calculated on booking save
- **Commission Slip PDF** — Printable monthly commission statement

### Settings & Branding
- **PDF Header Image** — Shown in PDF & Bulk PDF (not in direct print)
- **Print Letterhead** — Shown in Direct Print (for physical letterhead paper)
- **Footer Image** — Fixed at page bottom in PDF only
- **Signature Images** — 4 configurable signatories with adjustable height
- **Margin Control** — Separate margins for single/bulk/bill × print/pdf

### Patient Portal
- Patients login to download their own finalized reports
- QR code on report → opens all reports for that patient as bulk PDF

### Advanced Features
- AI-powered report interpretation
- SMS/WhatsApp notifications on report finalization
- Critical alerts tracking
- Home collection scheduling
- Insurance claims management
- Inventory tracking
- Quality control log
- Revenue reports
- Analyser integration (HL7/FHIR)

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Migrations

Run after each update:
```bash
python manage.py migrate
```

New migrations in v1.1:
- `0015_doctor_linked_user` — Doctor portal access
- `0016_labsettings_pdf_header_image` — PDF header image field
- `0017_labsettings_signer_image_height` — Signature size control

## Tech Stack

- **Backend**: Django 4.x, SQLite (dev) / PostgreSQL (prod)
- **Frontend**: Vanilla HTML/CSS/JS, no framework dependencies
- **PDF**: Browser print-to-PDF with CSS `@page` rules
- **QR**: `qrcode` Python library
- **AI**: Anthropic Claude API (optional)
- **SMS**: MSG91 / Twilio (optional)

## Project Structure

```
pathlab_v2_fixed/
├── core/
│   ├── settings.py      # Django configuration + APP_VERSION
│   └── urls.py          # Root URL dispatcher
├── lab/
│   ├── models.py        # All database models
│   ├── views.py         # All view functions (1900+ lines)
│   ├── urls.py          # App URL patterns
│   ├── signals.py       # Auto-commission + report finalization signals
│   ├── middleware.py    # Pro Suite PIN protection
│   ├── context_processors.py  # Global template context (LAB, APP_VERSION)
│   ├── migrations/      # Database migrations
│   └── templates/lab/   # All HTML templates
└── media/branding/      # Uploaded images (logos, signatures, letterheads)
```
