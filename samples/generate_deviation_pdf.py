"""Build the sample deviation PDF. The committed PDF is what the demo uploads.

Regenerate from the repository root:

    backend/.venv/bin/python samples/generate_deviation_pdf.py

Falls back to Helvetica if DejaVu is not installed, so the script can run on Windows.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "DEV-2026-1184_atorvastatin_impurity.pdf"
INK = HexColor("#1b1914")
TEAL = HexColor("#0f5e57")
RULE = HexColor("#c9bead")
PAPER = HexColor("#fbf7f0")
SOFT = HexColor("#f3eee4")


def _font(name: str, filename: str, fallback: str) -> str:
    path = Path("/usr/share/fonts/truetype/dejavu") / filename
    if not path.is_file():
        return fallback
    pdfmetrics.registerFont(TTFont(name, str(path)))
    return name


SANS = _font("DejaVu", "DejaVuSans.ttf", "Helvetica")
SANS_BOLD = _font("DejaVuBold", "DejaVuSans-Bold.ttf", "Helvetica-Bold")
SERIF = _font("DejaVuSerif", "DejaVuSerif.ttf", "Times-Roman")
SERIF_BOLD = _font("DejaVuSerifBold", "DejaVuSerif-Bold.ttf", "Times-Bold")


def styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            "Mast",
            fontName=SERIF_BOLD,
            fontSize=15,
            leading=18,
            textColor=TEAL,
            spaceAfter=1,
        )
    )
    base.add(
        ParagraphStyle(
            "Sub",
            fontName=SANS,
            fontSize=8.5,
            leading=11,
            textColor=INK,
            spaceAfter=2,
        )
    )
    base.add(
        ParagraphStyle(
            "Sec",
            fontName=SERIF_BOLD,
            fontSize=11.5,
            leading=14,
            textColor=TEAL,
            spaceBefore=8,
            spaceAfter=3,
        )
    )
    base.add(
        ParagraphStyle(
            "Body",
            fontName=SANS,
            fontSize=9,
            leading=12.5,
            textColor=INK,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        )
    )
    base.add(
        ParagraphStyle(
            "Field",
            fontName=SANS,
            fontSize=8.5,
            leading=11,
            textColor=INK,
        )
    )
    base.add(
        ParagraphStyle(
            "BulletBody",
            fontName=SANS,
            fontSize=9,
            leading=12.2,
            textColor=INK,
        )
    )
    return base


def field_table(pairs: list[tuple[str, str]], style) -> Table:
    rows = []
    for label, value in pairs:
        rows.append(
            [
                Paragraph(f"<b>{label}</b>", style["Field"]),
                Paragraph(value, style["Field"]),
            ]
        )
    table = Table(rows, colWidths=[42 * mm, 128 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), SOFT),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("FONTNAME", (0, 0), (-1, -1), SANS),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.3, RULE),
            ]
        )
    )
    return table


def bullets(items: list[str], style) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style["BulletBody"]), leftIndent=8) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontName=SANS,
        bulletFontSize=8,
        spaceBefore=1,
        spaceAfter=4,
    )


def build() -> None:
    style = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="DEV-2026-1184 Atorvastatin impurity and assay OOS",
        author="Northline API Works — Quality Unit",
    )
    story = [
        Paragraph("NORTHLINE API WORKS", style["Mast"]),
        Paragraph(
            "Quality Unit · Hyderabad · Deviation report QA-FRM-014 Rev 6 · Controlled copy",
            style["Sub"],
        ),
        HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=8),
        Paragraph("Deviation report — open at initiation", style["Sec"]),
        field_table(
            [
                ("Deviation number", "DEV-2026-1184"),
                ("Title", "RS-3 and assay out of specification after crystallization excursion"),
                ("Date/time of occurrence", "12 March 2026, 14:40 IST"),
                ("Date/time of detection", "14 March 2026, 09:15 IST, during QC HPLC review"),
                ("Site", "Northline API Works, Hyderabad"),
                ("Area", "Crystallization bay 2"),
                ("Equipment", "Crystallizer CR-300; cooling-water loop CW-02; valve V-17"),
                ("Product", "Atorvastatin calcium, crystalline API"),
                ("Batch / lot", "ATV-CA-26-0142"),
                ("Process stage", "Final crystallization and isolation"),
                ("Proposed classification", "Major — specification failure, batch quarantined, not shipped"),
                ("Raised by", "L. Joseph, production supervisor, B shift"),
                ("Received by QA", "14 March 2026, 09:40 IST"),
            ],
            style,
        ),
        Paragraph("Description", style["Sec"]),
        Paragraph(
            "QC reported related substance RS-3 (desfluoro impurity) at 0.18% against a specification "
            "of NMT 0.15% for atorvastatin calcium batch ATV-CA-26-0142. Assay on the anhydrous basis "
            "was 98.2% against 98.5–101.5%. Both results are out of specification. The batch was set "
            "to Quarantine in the inventory system and has not been shipped. It is intended for EU CEP "
            "supply. OOS procedure QA-SOP-014 has been initiated. The previous batch from the same "
            "crystallizer, ATV-CA-26-0141, met RS-3 at 0.09%.",
            style["Body"],
        ),
        Paragraph(
            "The batch record shows that during the crystallization hold the jacket temperature rose "
            "from the target of 8°C to 17°C and stayed there for 46 minutes, from 14:22 to 15:08 on "
            "12 March 2026. Operator R. Menon wrote in the B-shift log: cooling water pressure "
            "fluctuating, V-17 hunting. Maintenance work order WO-88421 was open on the CW-02 strainer. "
            "The strainer was cleaned on 11 March, but the differential-pressure alarm was left "
            "suppressed in the DCS until 13 March 2026 at 06:00.",
            style["Body"],
        ),
        Paragraph("Results at detection", style["Sec"]),
        field_table(
            [
                ("Test", "Result / specification / call"),
                ("Related substance RS-3", "0.18% / NMT 0.15% / OOS"),
                ("Assay, anhydrous basis", "98.2% / 98.5–101.5% / OOS"),
                ("Previous batch ATV-CA-26-0141 RS-3", "0.09% / NMT 0.15% / conforms"),
            ],
            style,
        ),
        Paragraph("Immediate actions", style["Sec"]),
        bullets(
            [
                "Batch ATV-CA-26-0142 status set to Quarantine. No material has been shipped.",
                "Crystallizer CR-300 tagged out of service pending an engineering check of valve V-17 and loop CW-02.",
                "Retained samples pulled. Mother-liquor samples from the crystallization have been requested and are not yet tested.",
                "HPLC worksheet held with the batch record. Analyst noted manual integration of the RS-3 peak.",
            ],
            style,
        ),
        Paragraph("Facts recorded at initiation", style["Sec"]),
        bullets(
            [
                "Solvent lot IPA-8891 is the same lot used for batch ATV-CA-26-0141 and for two earlier conforming batches. The CoA conforms.",
                "Seed lot SL-77 CoA conforms. The charge was recorded as 1.2 kg against a batch-record target of 1.5 kg. The weighing printout from balance BAL-QC-04 is missing from the batch record. A second-person verification signature is present but illegible.",
                "HPLC method STM-ATV-RS revision 7. System suitability passed. The analyst noted that the RS-3 standard was added mid-sequence because it had not arrived when the SST sequence was started. Integration of RS-3 was manual.",
                "During isolation, cleanroom humidity was 62% against a limit of NMT 55% for about 3 hours, coinciding with an AHU-4 filter change. Isolation was after the crystallization excursion.",
            ],
            style,
        ),
        Paragraph("Impact noted by production — QA to confirm", style["Sec"]),
        Paragraph(
            "Product quality: two specification failures on the release tests. The batch cannot be "
            "released on these results. Patient safety: no patient exposure is identified; the batch "
            "has not left the site and has not been administered. Regulatory: the batch was planned "
            "for EU CEP supply, so a confirmed OOS must be investigated under QA-SOP-014 before any "
            "disposition. Batch disposition at the time of this report: Quarantine.",
            style["Body"],
        ),
        Paragraph("Not yet established", style["Sec"]),
        bullets(
            [
                "Whether the RS-3 peak is confirmed on reinjection with a complete system-suitability sequence, including the RS-3 standard present from the start.",
                "Who suppressed the CW-02 differential-pressure alarm, and the DCS audit trail for that change.",
                "The maintenance history of valve V-17, beyond the note that it was hunting.",
                "The missing balance printout for the seed charge on BAL-QC-04.",
                "A formal interview with operator R. Menon.",
            ],
            style,
        ),
        Spacer(1, 6),
        Paragraph(
            "This report records the deviation at initiation. It does not conclude a root cause. "
            "Investigation method to be agreed by QA: 5 Whys and an Ishikawa diagram covering Man, "
            "Machine, Method, Material, Measurement, and Environment.",
            style["Body"],
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"wrote {OUT}")


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, 12 * mm, A4[0], 1.2, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont(SANS, 8)
    canvas.drawString(16 * mm, 6 * mm, "DEV-2026-1184 · Northline API Works · Uncontrolled once printed")
    canvas.drawRightString(A4[0] - 16 * mm, 6 * mm, f"Page {doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    build()
