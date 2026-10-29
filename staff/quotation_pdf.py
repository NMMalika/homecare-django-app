
from io import BytesIO
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.units import mm
from xml.sax.saxutils import escape
from homecare.models import Quotation
from core.models import SiteSettings


def quotation_pdf_response(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related("homecare_request", "consultation"), pk=pk
    )
    business = SiteSettings.load()
    generated_at = timezone.localtime(timezone.now())
    buff = BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=(210 * mm, 297 * mm),
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=25 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BrandCustom",
            parent=styles["Heading1"],
            fontSize=19,
            leading=23,
            textColor=colors.HexColor("#12556a"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MutedCustom",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#607483"),
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="RightCustom", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=10
        )
    )
    story = []

    def p(value, style="Normal"):
        return Paragraph(escape(str(value if value is not None else "")), styles[style])

    header = []
    if business.logo:
        try:
            if business.logo.storage.exists(business.logo.name):
                with business.logo.open("rb") as logo_file:
                    from PIL import Image as PILImage
                    import io

                    raw = logo_file.read()
                    im = PILImage.open(io.BytesIO(raw))
                    im.thumbnail((400, 400))
                    rgb = im.convert("RGB")
                    logo_buf = BytesIO()
                    rgb.save(logo_buf, format="PNG")
                    logo_buf.seek(0)
                    header.append(
                        Image(
                            logo_buf, width=28 * mm, height=28 * mm, kind="proportional"
                        )
                    )
        except (OSError, ValueError):
            pass
    heading = [
        p(business.business_name or "Hands-On Health", "BrandCustom"),
        p(business.tagline or "Professional home-based care", "MutedCustom"),
    ]
    if header:
        table = Table([[header[0], heading]], colWidths=[35 * mm, 135 * mm])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(table)
    else:
        story.extend(heading)
    story.extend(
        [
            Spacer(1, 9 * mm),
            p(f"QUOTATION #{quotation.pk}", "Heading2"),
            p(f"Generated: {generated_at:%d %B %Y, %H:%M %Z}", "MutedCustom"),
            Spacer(1, 5 * mm),
        ]
    )
    person = quotation.consultation or quotation.homecare_request
    if quotation.consultation:
        client = f"{person.first_name} {person.last_name}".strip()
        kind = "Consultation / Appointment"
    elif person:
        client = person.full_name
        kind = "Home Care"
    else:
        client = "Not assigned"
        kind = "Quotation"
    rows = [
        ["Client", client],
        ["Type", kind],
        ["Email", getattr(person, "email", "") or "—"],
        ["Phone", getattr(person, "phone", "") or "—"],
        ["Payment status", quotation.get_payment_status_display()],
        [
            "Sent at",
            (
                timezone.localtime(quotation.sent_at).strftime("%d %b %Y %H:%M")
                if quotation.sent_at
                else "Not sent"
            ),
        ],
        [
            "Payment deadline",
            (
                timezone.localtime(quotation.payment_deadline).strftime(
                    "%d %b %Y %H:%M"
                )
                if quotation.payment_deadline
                else "Not specified"
            ),
        ],
    ]
    if getattr(person, "location", None):
        rows.insert(4, ["Location", person.location])
    info = Table(
        [[p(a), p(b)] for a, b in rows], colWidths=[42 * mm, 128 * mm], hAlign="LEFT"
    )
    info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e3eaf0")),
            ]
        )
    )
    story.extend([info, Spacer(1, 8 * mm), p("Financial breakdown", "Heading2")])
    money = lambda x: f"N$ {Decimal(x or 0):,.2f}"
    financial = [
        ["Services subtotal", money(quotation.base_amount)],
        ["Transportation", money(quotation.transportation_fee)],
        ["Discount", f"- {money(quotation.discount_amount)}"],
        ["TOTAL", money(quotation.amount)],
    ]
    t = Table(
        [[p(a), p(b, "RightCustom")] for a, b in financial],
        colWidths=[100 * mm, 70 * mm],
    )
    t.setStyle(
        TableStyle(
            [
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -2),
                    [colors.white, colors.HexColor("#f5f9fa")],
                ),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e4f5f2")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(t)
    if quotation.description:
        story.extend(
            [
                Spacer(1, 8 * mm),
                p("Quotation description", "Heading2"),
                Paragraph(
                    escape(quotation.description).replace("\n", "<br/>"),
                    styles["Normal"],
                ),
            ]
        )
    contact = " | ".join(
        str(x) for x in [business.phone, business.email, business.website] if x
    )
    address = ", ".join(
        str(x) for x in [business.address, business.city, business.country] if x
    )

    def footer(canvas, document):
        canvas.saveState()
        w, h = doc.pagesize
        canvas.setStrokeColor(colors.HexColor("#cbdfe3"))
        canvas.line(18 * mm, 21 * mm, w - 18 * mm, 21 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526879"))
        canvas.drawString(
            18 * mm, 16 * mm, (business.business_name or "Hands-On Health")[:70]
        )
        canvas.drawString(18 * mm, 12 * mm, address[:105])
        canvas.drawString(18 * mm, 8 * mm, contact[:110])
        canvas.drawRightString(
            w - 18 * mm,
            16 * mm,
            f"Generated {generated_at:%d %b %Y %H:%M} | Page {document.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(buff.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Hands-On-Health-Quotation-{quotation.pk}.pdf"'
    )
    response["Cache-Control"] = "private, no-store"
    return response
