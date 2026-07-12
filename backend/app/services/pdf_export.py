"""
Board-ready PDF Export Service
Generates professional PDF packs for Leadership Pack, Weekly Brief, National Pulse.
Uses reportlab (installed in requirements).
"""
import io
from datetime import datetime, timezone
from typing import Optional


def _clean(text: str) -> str:
    """Remove markdown bold markers for PDF output."""
    if not text:
        return ""
    return text.replace("**", "").replace("*", "")


def generate_leadership_pack_pdf(data: dict) -> bytes:
    """Generate board-ready Leadership Pack PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        return b""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    # Colours
    NAVY = HexColor("#0f172a")
    BLUE = HexColor("#3b82f6")
    TEAL = HexColor("#14b8a6")
    SLATE = HexColor("#475569")
    LIGHT = HexColor("#f8fafc")
    RED = HexColor("#ef4444")
    AMBER = HexColor("#f59e0b")

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    def style(name, parent="Normal", **kwargs):
        return ParagraphStyle(name, parent=styles[parent], **kwargs)

    title_style = style("Title", fontSize=22, textColor=white, spaceAfter=4, fontName="Helvetica-Bold")
    subtitle_style = style("Subtitle", fontSize=10, textColor=HexColor("#94a3b8"), spaceAfter=2)
    h1 = style("H1", fontSize=14, textColor=BLUE, spaceBefore=16, spaceAfter=6, fontName="Helvetica-Bold")
    h2 = style("H2", fontSize=11, textColor=HexColor("#1e3a5f"), spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold")
    body = style("Body", fontSize=9, textColor=HexColor("#1e293b"), spaceAfter=4, leading=14)
    label = style("Label", fontSize=8, textColor=HexColor("#334155"), spaceAfter=2, fontName="Helvetica-Bold")
    conf = style("Conf", fontSize=8, textColor=HexColor("#0d9488"), spaceAfter=2)
    footer_style = style("Footer", fontSize=7, textColor=SLATE, alignment=TA_CENTER)

    story = []
    generated = data.get("generated_at", "")
    period = data.get("period_days", 7)
    gen_dt = datetime.fromisoformat(generated).strftime("%d %B %Y, %H:%M UTC") if generated else ""

    # Cover header
    story.append(Table(
        [[Paragraph("NATIONAL & DIASPORA INTELLIGENCE PLATFORM (NDIP)", title_style)],
         [Paragraph("Leadership Intelligence Pack", subtitle_style)],
         [Paragraph(f"{gen_dt}  ·  {period}-day analysis window", subtitle_style)]],
        colWidths=[17*cm],
        style=TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), NAVY),
            ("PADDING", (0,0), (-1,-1), 12),
            ("TOPPADDING", (0,0), (0,0), 20),
            ("BOTTOMPADDING", (0,-1), (0,-1), 20),
            ("ROUNDEDCORNERS", (0,0), (-1,-1), 6),
        ])
    ))
    story.append(Spacer(1, 16))

    # Section 1: Executive Summary
    story.append(Paragraph("SECTION 1 — EXECUTIVE SUMMARY", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))
    story.append(Paragraph(_clean(data.get("executive_summary", "")), body))

    if data.get("national_context"):
        story.append(Spacer(1, 6))
        story.append(Paragraph("NATIONAL CONTEXT", label))
        story.append(Paragraph(_clean(data.get("national_context", "")), body))

    if data.get("comparative_intelligence"):
        story.append(Spacer(1, 6))
        story.append(Paragraph("COMPARATIVE INTELLIGENCE", label))
        for c in data["comparative_intelligence"]:
            story.append(Paragraph(f"• {_clean(c)}", body))

    # Section 2: Narrative Assessments
    story.append(PageBreak())
    story.append(Paragraph("SECTION 2 — NARRATIVE ASSESSMENT", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))

    for a in (data.get("narrative_assessments") or [])[:6]:
        story.append(Paragraph(a["narrative"].upper(), h2))
        story.append(Paragraph(f"Share of voice: {a['share_of_voice']}%  ·  Sentiment: {a['sentiment_label']}  ·  Confidence: {a['confidence_label']}", label))

        for key, lbl in [("what_happened","What happened"), ("why_it_matters","Why it matters"),
                          ("what_changed","What changed"), ("leadership_considerations","Leadership action")]:
            if a.get(key):
                story.append(Paragraph(lbl.upper(), label))
                story.append(Paragraph(_clean(a[key]), body))
        story.append(Spacer(1, 6))

    # Section 4: Risks & Opportunities
    story.append(PageBreak())
    story.append(Paragraph("SECTION 4 — RISKS & OPPORTUNITIES", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))

    story.append(Paragraph("RISKS", h2))
    risks = data.get("risks") or []
    non_info = [r for r in risks if r.get("level") != "Information"]
    if not non_info:
        story.append(Paragraph("No critical risks identified this period.", body))
    else:
        for r in non_info:
            level_color = RED if r["level"] == "Critical" else AMBER if r["level"] == "Warning" else SLATE
            story.append(Paragraph(f"[{r['level']}] {_clean(r['title'])}", style("RLevel", fontSize=9, textColor=level_color, fontName="Helvetica-Bold", spaceAfter=2)))
            story.append(Paragraph(_clean(r["detail"]), body))
            story.append(Paragraph(f"Action: {r['action']}", label))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))
    story.append(Paragraph("OPPORTUNITIES", h2))
    opps = data.get("opportunities") or []
    if not opps:
        story.append(Paragraph("No specific opportunities identified.", body))
    else:
        for o in opps[:4]:
            story.append(Paragraph(f"[{o['rank']}] {_clean(o['title'])}", style("ORank", fontSize=9, textColor=TEAL, fontName="Helvetica-Bold", spaceAfter=2)))
            story.append(Paragraph(_clean(o["detail"]), body))
            story.append(Paragraph(f"Action: {o['action']}", label))
            story.append(Spacer(1, 4))

    # Section 5: Outlook
    story.append(PageBreak())
    story.append(Paragraph("SECTION 5 — EXECUTIVE OUTLOOK", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))
    outlook = data.get("outlook") or {}
    for key, lbl in [("7_day","7-Day Outlook"),("14_day","14-Day Outlook"),("30_day","30-Day Outlook")]:
        if outlook.get(key):
            story.append(Paragraph(lbl.upper(), label))
            story.append(Paragraph(_clean(outlook[key]), body))
            story.append(Spacer(1, 4))

    # Section 6: Confidence
    story.append(Spacer(1, 8))
    story.append(Paragraph("SECTION 6 — CONFIDENCE STATEMENT", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))
    cs = data.get("confidence_statement") or {}
    if cs:
        story.append(Paragraph(_clean(cs.get("summary", "")), body))
        for lim in cs.get("limitations", []):
            story.append(Paragraph(f"• {lim}", body))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"RTIFN National & Diaspora Intelligence Platform (NDIP)  ·  Leadership Intelligence Pack  ·  {gen_dt}  ·  Aggregated, anonymised data only  ·  Not for public distribution",
        footer_style
    ))

    doc.build(story)
    return buffer.getvalue()
