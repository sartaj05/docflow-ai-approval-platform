import io
from pathlib import Path

import qrcode
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4


# ==========================================================
# URL / image helpers
# ==========================================================

def get_app_url():
    return getattr(settings, "DOCFLOW_APP_URL", "http://127.0.0.1:8000").rstrip("/")


def build_verify_url(document_request):
    return f"{get_app_url()}/reports/verify/{document_request.pk}/"


def build_certificate_verify_url(certificate_signature):
    if certificate_signature and certificate_signature.verification_url:
        return certificate_signature.verification_url

    if certificate_signature:
        return f"{get_app_url()}/reports/certificates/verify/{certificate_signature.verification_code}/"

    return ""


def get_logo_path(organization):
    if organization and organization.logo:
        try:
            logo_path = organization.logo.path

            if Path(logo_path).exists():
                return logo_path
        except Exception:
            return None

    return None


def get_seal_path(organization):
    if organization and organization.seal_image:
        try:
            seal_path = organization.seal_image.path

            if Path(seal_path).exists():
                return seal_path
        except Exception:
            return None

    return None


def get_signature_path(certificate_signature):
    if not certificate_signature:
        return None

    signer = certificate_signature.signed_by

    if not signer:
        return None

    profile = getattr(signer, "profile", None)

    if not profile or not profile.signature_image:
        return None

    try:
        signature_path = profile.signature_image.path

        if Path(signature_path).exists():
            return signature_path
    except Exception:
        return None

    return None


def create_qr_image_from_text(text):
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=2,
    )

    qr.add_data(text)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer

def create_certificate_qr_image(verification_url):
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=2,
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer
def create_qr_image(document_request):
    verify_url = build_verify_url(document_request)
    return create_qr_image_from_text(verify_url)


def create_certificate_qr_image(certificate_signature, document_request):
    if certificate_signature:
        verify_url = build_certificate_verify_url(certificate_signature)
    else:
        verify_url = build_verify_url(document_request)

    return create_qr_image_from_text(verify_url)


# ==========================================================
# Styles
# ==========================================================

def get_pdf_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="DocFlowTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallMuted",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="NormalWrap",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="RightSmall",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#64748b"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="CertificateTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#166534"),
            spaceAfter=14,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CertificateText",
            parent=styles["Normal"],
            fontSize=11,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1f2937"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="CertificateSmallCenter",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748b"),
        )
    )

    return styles


# ==========================================================
# Header / footer / watermark
# ==========================================================

def draw_header_footer(canvas, doc, organization=None, watermark_text="DOCFLOW AI"):
    canvas.saveState()

    logo_path = get_logo_path(organization)

    if logo_path:
        try:
            canvas.drawImage(
                logo_path,
                18 * mm,
                PAGE_HEIGHT - 25 * mm,
                width=18 * mm,
                height=18 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    org_name = organization.name if organization else "DocFlow AI"
    org_email = organization.email if organization else ""

    canvas.setFillColor(colors.HexColor("#0f172a"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(40 * mm, PAGE_HEIGHT - 15 * mm, org_name)

    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(40 * mm, PAGE_HEIGHT - 20 * mm, org_email)

    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.line(
        18 * mm,
        PAGE_HEIGHT - 30 * mm,
        PAGE_WIDTH - 18 * mm,
        PAGE_HEIGHT - 30 * mm,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(
        18 * mm,
        12 * mm,
        f"Generated at {timezone.localtime().strftime('%d %b %Y, %I:%M %p')}",
    )

    page_text = f"Page {doc.page}"
    canvas.drawRightString(PAGE_WIDTH - 18 * mm, 12 * mm, page_text)

    draw_watermark(canvas, watermark_text)

    canvas.restoreState()


def draw_watermark(canvas, watermark_text):
    canvas.saveState()

    canvas.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
    canvas.rotate(35)

    canvas.setFillColor(colors.Color(0.1, 0.1, 0.1, alpha=0.06))
    canvas.setFont("Helvetica-Bold", 54)

    text_width = stringWidth(watermark_text, "Helvetica-Bold", 54)
    canvas.drawString(-text_width / 2, 0, watermark_text)

    canvas.restoreState()


# ==========================================================
# Table helpers
# ==========================================================

def make_key_value_table(rows, col_widths=None):
    if col_widths is None:
        col_widths = [45 * mm, 120 * mm]

    styles = get_pdf_styles()
    data = []

    for key, value in rows:
        data.append(
            [
                Paragraph(f"<b>{key}</b>", styles["NormalWrap"]),
                Paragraph(str(value or "-"), styles["NormalWrap"]),
            ]
        )

    table = Table(data, colWidths=col_widths)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


def get_default_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ]
    )


def make_status_badge_text(value):
    return value.replace("_", " ").title() if value else "-"


def format_datetime(value):
    if not value:
        return "-"

    return timezone.localtime(value).strftime("%d %b %Y, %I:%M %p")


def get_watermark_text(request, document_request):
    ip_address = "-"

    if request:
        ip_address = request.META.get(
            "HTTP_X_FORWARDED_FOR",
            request.META.get("REMOTE_ADDR", "-"),
        )

        if "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

    now_text = timezone.localtime().strftime("%d %b %Y %I:%M %p")

    return f"{document_request.request_number} | {ip_address} | {now_text}"


# ==========================================================
# Request summary PDF
# ==========================================================

def generate_request_summary_pdf(document_request, request=None):
    buffer = io.BytesIO()
    styles = get_pdf_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=38 * mm,
        bottomMargin=20 * mm,
        title=f"{document_request.request_number} Summary",
    )

    elements = []

    elements.append(Paragraph("Approval Request Summary", styles["DocFlowTitle"]))
    elements.append(Spacer(1, 8))

    qr_buffer = create_qr_image(document_request)
    qr_img = Image(qr_buffer, width=28 * mm, height=28 * mm)

    summary_rows = [
        ("Request Number", document_request.request_number),
        ("Title", document_request.title),
        ("Organization", document_request.organization.name if document_request.organization else "-"),
        ("Department", document_request.department.name if document_request.department else "-"),
        ("Created By", document_request.created_by.display_name if document_request.created_by else "-"),
        ("Workflow", document_request.workflow.name if document_request.workflow else "-"),
        ("Category", document_request.get_category_display()),
        ("Priority", document_request.get_priority_display()),
        ("Status", document_request.get_status_display()),
        (
            "Risk Level",
            document_request.get_risk_level_display()
            if document_request.risk_level
            else "Pending",
        ),
        ("Created At", format_datetime(document_request.created_at)),
        ("Submitted At", format_datetime(document_request.submitted_at)),
        ("Approved At", format_datetime(document_request.approved_at)),
        ("Rejected At", format_datetime(document_request.rejected_at)),
    ]

    main_info = make_key_value_table(summary_rows, col_widths=[42 * mm, 95 * mm])

    top_table = Table(
        [[main_info, qr_img]],
        colWidths=[140 * mm, 30 * mm],
    )

    top_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )

    elements.append(top_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Description", styles["SectionTitle"]))
    elements.append(Paragraph(document_request.description or "-", styles["NormalWrap"]))

    elements.append(Paragraph("AI Analysis", styles["SectionTitle"]))

    ai_rows = [
        ("AI Summary", document_request.ai_summary or "Pending AI processing"),
        ("AI Category", document_request.ai_category or "-"),
        ("Risk Notes", document_request.risk_notes or "-"),
        ("Extracted Data", document_request.ai_extracted_data or "-"),
    ]

    elements.append(make_key_value_table(ai_rows))
    elements.append(Spacer(1, 10))

    attachments = document_request.attachments.select_related(
        "uploaded_by"
    ).order_by("created_at")

    elements.append(Paragraph("Attached Documents", styles["SectionTitle"]))

    if attachments.exists():
        attachment_data = [
            [
                Paragraph("<b>File</b>", styles["NormalWrap"]),
                Paragraph("<b>Type</b>", styles["NormalWrap"]),
                Paragraph("<b>Size</b>", styles["NormalWrap"]),
                Paragraph("<b>Uploaded By</b>", styles["NormalWrap"]),
                Paragraph("<b>Date</b>", styles["NormalWrap"]),
            ]
        ]

        for item in attachments:
            attachment_data.append(
                [
                    Paragraph(item.original_filename or "-", styles["NormalWrap"]),
                    Paragraph(item.display_file_type or "-", styles["NormalWrap"]),
                    Paragraph(f"{item.file_size_mb} MB", styles["NormalWrap"]),
                    Paragraph(
                        item.uploaded_by.display_name if item.uploaded_by else "-",
                        styles["NormalWrap"],
                    ),
                    Paragraph(format_datetime(item.created_at), styles["NormalWrap"]),
                ]
            )

        table = Table(
            attachment_data,
            colWidths=[55 * mm, 25 * mm, 20 * mm, 38 * mm, 28 * mm],
            repeatRows=1,
        )

        table.setStyle(get_default_table_style())
        elements.append(table)
    else:
        elements.append(Paragraph("No documents uploaded.", styles["SmallMuted"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Approval Workflow", styles["SectionTitle"]))

    steps = document_request.approval_steps.select_related(
        "assigned_to"
    ).order_by("step_order")

    if steps.exists():
        step_data = [
            [
                Paragraph("<b>Step</b>", styles["NormalWrap"]),
                Paragraph("<b>Approver</b>", styles["NormalWrap"]),
                Paragraph("<b>Role</b>", styles["NormalWrap"]),
                Paragraph("<b>Status</b>", styles["NormalWrap"]),
                Paragraph("<b>Due</b>", styles["NormalWrap"]),
            ]
        ]

        for step in steps:
            step_data.append(
                [
                    Paragraph(str(step.step_order), styles["NormalWrap"]),
                    Paragraph(
                        step.assigned_to.display_name if step.assigned_to else "-",
                        styles["NormalWrap"],
                    ),
                    Paragraph(step.role_required or "-", styles["NormalWrap"]),
                    Paragraph(make_status_badge_text(step.status), styles["NormalWrap"]),
                    Paragraph(format_datetime(step.due_at), styles["NormalWrap"]),
                ]
            )

        step_table = Table(
            step_data,
            colWidths=[15 * mm, 45 * mm, 35 * mm, 30 * mm, 42 * mm],
            repeatRows=1,
        )

        step_table.setStyle(get_default_table_style())
        elements.append(step_table)
    else:
        elements.append(Paragraph("No workflow steps generated.", styles["SmallMuted"]))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Approval Actions Timeline", styles["SectionTitle"]))

    actions = document_request.approval_actions.select_related(
        "action_by",
        "step",
    ).order_by("created_at")

    if actions.exists():
        action_data = [
            [
                Paragraph("<b>Date</b>", styles["NormalWrap"]),
                Paragraph("<b>Action</b>", styles["NormalWrap"]),
                Paragraph("<b>By</b>", styles["NormalWrap"]),
                Paragraph("<b>Comment</b>", styles["NormalWrap"]),
            ]
        ]

        for action in actions:
            action_data.append(
                [
                    Paragraph(format_datetime(action.created_at), styles["NormalWrap"]),
                    Paragraph(action.get_action_type_display(), styles["NormalWrap"]),
                    Paragraph(
                        action.action_by.display_name if action.action_by else "System",
                        styles["NormalWrap"],
                    ),
                    Paragraph(action.comment or "-", styles["NormalWrap"]),
                ]
            )

        action_table = Table(
            action_data,
            colWidths=[35 * mm, 30 * mm, 35 * mm, 67 * mm],
            repeatRows=1,
        )

        action_table.setStyle(get_default_table_style())
        elements.append(action_table)
    else:
        elements.append(Paragraph("No approval actions recorded.", styles["SmallMuted"]))

    elements.append(Spacer(1, 16))
    elements.append(
        Paragraph(
            f"Verification URL: {build_verify_url(document_request)}",
            styles["SmallMuted"],
        )
    )

    watermark = get_watermark_text(request, document_request)

    doc.build(
        elements,
        onFirstPage=lambda canvas, doc_obj: draw_header_footer(
            canvas,
            doc_obj,
            document_request.organization,
            watermark,
        ),
        onLaterPages=lambda canvas, doc_obj: draw_header_footer(
            canvas,
            doc_obj,
            document_request.organization,
            watermark,
        ),
    )

    buffer.seek(0)
    return buffer

def generate_approval_certificate_pdf(
    document_request,
    request=None,
    certificate_signature=None,
    verification_url=None,
):
    buffer = io.BytesIO()
    styles = get_pdf_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24 * mm,
        leftMargin=24 * mm,
        topMargin=42 * mm,
        bottomMargin=22 * mm,
        title=f"{document_request.request_number} Approval Certificate",
    )

    elements = []

    certificate_title = "Approval Certificate"

    if document_request.organization and document_request.organization.certificate_header_text:
        certificate_title = document_request.organization.certificate_header_text

    elements.append(Spacer(1, 18))
    elements.append(Paragraph(certificate_title, styles["CertificateTitle"]))

    elements.append(
        Paragraph(
            "This certificate confirms that the following approval request has been processed and digitally verified through DocFlow AI.",
            styles["CertificateText"],
        )
    )

    elements.append(Spacer(1, 18))

    if certificate_signature and not verification_url:
        verification_url = certificate_signature.verification_url

    if not verification_url and certificate_signature:
        verification_url = f"{get_app_url()}/reports/certificates/verify/{certificate_signature.verification_code}/"

    qr_img = None

    if verification_url:
        certificate_qr_buffer = create_certificate_qr_image(verification_url)
        qr_img = Image(
            certificate_qr_buffer,
            width=32 * mm,
            height=32 * mm,
        )

    certificate_rows = [
        ("Request Number", document_request.request_number),
        ("Request Title", document_request.title),
        ("Organization", document_request.organization.name if document_request.organization else "-"),
        ("Department", document_request.department.name if document_request.department else "-"),
        ("Requested By", document_request.created_by.display_name if document_request.created_by else "-"),
        ("Category", document_request.get_category_display()),
        ("Priority", document_request.get_priority_display()),
        ("Final Status", document_request.get_status_display()),
        (
            "Approved At",
            timezone.localtime(document_request.approved_at).strftime("%d %b %Y, %I:%M %p")
            if document_request.approved_at
            else "-",
        ),
    ]

    if certificate_signature:
        certificate_rows.extend(
            [
                ("Verification Code", certificate_signature.verification_code),
                ("Certificate UUID", certificate_signature.certificate_uuid),
                ("Certificate Hash", certificate_signature.certificate_hash),
                (
                    "Signed At",
                    timezone.localtime(certificate_signature.signed_at).strftime("%d %b %Y, %I:%M %p")
                    if certificate_signature.signed_at
                    else "-",
                ),
                (
                    "Certificate Status",
                    "Valid" if certificate_signature.is_valid else "Invalidated",
                ),
            ]
        )

    main_info = make_key_value_table(
        certificate_rows,
        col_widths=[42 * mm, 92 * mm],
    )

    if qr_img:
        qr_block = Table(
            [
                [qr_img],
                [
                    Paragraph(
                        "<b>Scan to Verify</b>",
                        styles["CertificateText"],
                    )
                ],
                [
                    Paragraph(
                        certificate_signature.verification_code if certificate_signature else "",
                        styles["SmallMuted"],
                    )
                ],
            ],
            colWidths=[36 * mm],
        )

        qr_block.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        top_table = Table(
            [[main_info, qr_block]],
            colWidths=[132 * mm, 38 * mm],
        )

        top_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ]
            )
        )

        elements.append(top_table)
    else:
        elements.append(main_info)

    elements.append(Spacer(1, 22))

    if document_request.status == "APPROVED":
        approval_text = (
            f"The request <b>{document_request.request_number}</b> has been approved "
            "through the defined approval workflow."
        )
    elif document_request.status == "REJECTED":
        approval_text = (
            f"The request <b>{document_request.request_number}</b> has been rejected "
            "during the approval workflow."
        )
    else:
        approval_text = (
            f"The request <b>{document_request.request_number}</b> is currently "
            f"in <b>{document_request.get_status_display()}</b> status."
        )

    elements.append(Paragraph(approval_text, styles["CertificateText"]))
    elements.append(Spacer(1, 22))

    if certificate_signature and not certificate_signature.is_valid:
        elements.append(
            Paragraph(
                "<b>Warning:</b> This certificate has been invalidated.",
                styles["CertificateText"],
            )
        )

        if certificate_signature.invalidation_reason:
            elements.append(
                Paragraph(
                    f"Reason: {certificate_signature.invalidation_reason}",
                    styles["NormalWrap"],
                )
            )

        elements.append(Spacer(1, 16))

    steps = document_request.approval_steps.select_related("assigned_to").order_by("step_order")

    elements.append(Paragraph("Approval Chain", styles["SectionTitle"]))

    if steps.exists():
        step_data = [
            [
                Paragraph("<b>Step</b>", styles["NormalWrap"]),
                Paragraph("<b>Approver</b>", styles["NormalWrap"]),
                Paragraph("<b>Status</b>", styles["NormalWrap"]),
                Paragraph("<b>Decision Time</b>", styles["NormalWrap"]),
            ]
        ]

        for step in steps:
            decision_time = "-"

            if step.approved_at:
                decision_time = timezone.localtime(step.approved_at).strftime("%d %b %Y, %I:%M %p")

            if step.rejected_at:
                decision_time = timezone.localtime(step.rejected_at).strftime("%d %b %Y, %I:%M %p")

            step_data.append(
                [
                    Paragraph(str(step.step_order), styles["NormalWrap"]),
                    Paragraph(step.assigned_to.display_name if step.assigned_to else "-", styles["NormalWrap"]),
                    Paragraph(make_status_badge_text(step.status), styles["NormalWrap"]),
                    Paragraph(decision_time, styles["NormalWrap"]),
                ]
            )

        step_table = Table(
            step_data,
            colWidths=[18 * mm, 65 * mm, 38 * mm, 45 * mm],
            repeatRows=1,
        )

        step_table.setStyle(get_default_table_style())
        elements.append(step_table)
    else:
        elements.append(Paragraph("No workflow steps generated.", styles["SmallMuted"]))

    elements.append(Spacer(1, 24))

    signer_name = "System"
    signer_role = "Final Approver"

    if certificate_signature:
        signer_name = certificate_signature.signed_by_name or signer_name
        signer_role = certificate_signature.signed_by_role or signer_role

    seal_path = None

    if document_request.organization and document_request.organization.seal_image:
        try:
            if Path(document_request.organization.seal_image.path).exists():
                seal_path = document_request.organization.seal_image.path
        except Exception:
            seal_path = None

    signature_path = None

    if certificate_signature and certificate_signature.signed_by:
        signer_profile = getattr(certificate_signature.signed_by, "profile", None)

        if signer_profile and signer_profile.signature_image:
            try:
                if Path(signer_profile.signature_image.path).exists():
                    signature_path = signer_profile.signature_image.path
            except Exception:
                signature_path = None

    signature_cell_content = []

    if signature_path:
        signature_cell_content.append(
            Image(
                signature_path,
                width=45 * mm,
                height=18 * mm,
            )
        )
    else:
        signature_cell_content.append(
            Paragraph("Digitally Signed", styles["CertificateText"])
        )

    signature_cell_content.extend(
        [
            Spacer(1, 6),
            Paragraph(f"<b>{signer_name}</b>", styles["NormalWrap"]),
            Paragraph(signer_role, styles["SmallMuted"]),
        ]
    )

    seal_cell_content = []

    if seal_path:
        seal_cell_content.append(
            Image(
                seal_path,
                width=30 * mm,
                height=30 * mm,
            )
        )
    else:
        seal_cell_content.append(
            Paragraph("Organization Seal", styles["CertificateText"])
        )

    seal_cell_content.extend(
        [
            Spacer(1, 6),
            Paragraph(
                f"<b>{document_request.organization.name if document_request.organization else 'Organization'}</b>",
                styles["NormalWrap"],
            ),
            Paragraph("Official Seal", styles["SmallMuted"]),
        ]
    )

    sign_table = Table(
        [
            [
                signature_cell_content,
                seal_cell_content,
            ]
        ],
        colWidths=[82 * mm, 82 * mm],
    )

    sign_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    elements.append(sign_table)

    if verification_url:
        elements.append(Spacer(1, 14))
        elements.append(
            Paragraph(
                f"Verification URL: {verification_url}",
                styles["SmallMuted"],
            )
        )

    if document_request.organization and document_request.organization.certificate_footer_text:
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(
                document_request.organization.certificate_footer_text,
                styles["SmallMuted"],
            )
        )

    watermark = f"CERTIFICATE | {document_request.request_number}"

    doc.build(
        elements,
        onFirstPage=lambda canvas, doc_obj: draw_header_footer(
            canvas,
            doc_obj,
            document_request.organization,
            watermark,
        ),
        onLaterPages=lambda canvas, doc_obj: draw_header_footer(
            canvas,
            doc_obj,
            document_request.organization,
            watermark,
        ),
    )

    buffer.seek(0)
    return buffer