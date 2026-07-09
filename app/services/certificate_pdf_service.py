"""
app/services/certificate_pdf_service.py

Generates the QR code + PDF for an issued Certificate and uploads both to
Supabase storage. Called from certificate_service.issue_certificate()
right after the Certificate row is created.

QR encodes the public verification URL:
  {FRONTEND_URL}/verify/{certificate_number}
"""

import base64
import io
from pathlib import Path

import qrcode
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.core.config import settings
from app.models.certificate import Certificate
from app.services import storage_service

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _generate_qr_data_uri(verification_url: str) -> str:
    """Base64 data URI so the QR image embeds directly in the PDF without
    needing a separate network fetch during PDF rendering."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#4c1d95", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _generate_qr_png_bytes(verification_url: str) -> bytes:
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#4c1d95", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _render_certificate_html(certificate: Certificate, qr_data_uri: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("certificate.html")
    return template.render(
        student_name=certificate.student_name_snapshot,
        course_title=certificate.course_title_snapshot,
        certificate_number=certificate.certificate_number,
        issued_date=certificate.issued_at.strftime("%B %d, %Y") if certificate.issued_at else "",
        grade_percent=certificate.grade_percent,
        qr_code_data_uri=qr_data_uri,
    )


def generate_and_upload_certificate_assets(certificate: Certificate) -> dict:
    """
    Returns {"pdf_url": ..., "qr_code_url": ...}. Raises if Supabase storage
    isn't configured — caller decides whether that should block issuance
    or just leave the URLs empty for now (see certificate_service).
    """
    verification_url = f"{settings.FRONTEND_URL}/verify/{certificate.certificate_number}"

    qr_data_uri = _generate_qr_data_uri(verification_url)
    qr_png_bytes = _generate_qr_png_bytes(verification_url)

    html_content = _render_certificate_html(certificate, qr_data_uri)
    pdf_bytes = HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf()

    pdf_url = storage_service.upload_file(
        path=f"certificates/{certificate.certificate_number}.pdf",
        content=pdf_bytes,
        content_type="application/pdf",
    )
    qr_url = storage_service.upload_file(
        path=f"certificates/qr/{certificate.certificate_number}.png",
        content=qr_png_bytes,
        content_type="image/png",
    )

    return {"pdf_url": pdf_url, "qr_code_url": qr_url}
