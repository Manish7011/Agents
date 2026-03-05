"""
report.py — Markdown-aware PDF session report generator
Uses a line-by-line Markdown parser to render headings, bold, italic,
code blocks, inline code, lists, blockquotes, and horizontal rules
into proper ReportLab flowables. No KeepTogether wrapping — long AI
responses paginate freely across page boundaries.
"""

from io import BytesIO
from typing import List, Dict, Any
import re

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted, ListFlowable, ListItem,
)

# ── Palette ───────────────────────────────────────────────────────────────────
C_HUMAN_BG  = colors.HexColor("#E8F5E9")
C_AI_BG     = colors.HexColor("#F3F4F6")
C_HUMAN_HDR = colors.HexColor("#2E7D32")
C_AI_HDR    = colors.HexColor("#1565C0")
C_CODE_BG   = colors.HexColor("#1E1E1E")
C_CODE_FG   = colors.HexColor("#D4D4D4")
C_QUOTE_BG  = colors.HexColor("#FFF9C4")
C_BORDER    = colors.HexColor("#DADCE0")
C_TITLE     = colors.HexColor("#0D1B2A")
C_ACCENT    = colors.HexColor("#1A73E8")
C_H1        = colors.HexColor("#0D1B2A")
C_H2        = colors.HexColor("#1565C0")
C_H3        = colors.HexColor("#2E7D32")


def _build_styles(is_human: bool = False) -> dict:
    base = getSampleStyleSheet()
    bg = C_HUMAN_BG if is_human else C_AI_BG

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "report_title": ParagraphStyle(
            "ReportTitle", parent=base["Title"],
            textColor=C_TITLE, fontSize=20, spaceAfter=4,
        ),
        "session_id": ps("SessionId", fontSize=9,
                         textColor=colors.HexColor("#666666"), spaceAfter=2),
        "section_heading": ps(
            "SectionHeading", fontSize=13, fontName="Helvetica-Bold",
            textColor=C_TITLE, spaceBefore=14, spaceAfter=6,
        ),
        "human_label": ps(
            "HumanLabel", fontSize=8, fontName="Helvetica-Bold",
            textColor=colors.white, backColor=C_HUMAN_HDR,
            leftIndent=8, spaceBefore=8, spaceAfter=0, leading=14,
        ),
        "ai_label": ps(
            "AILabel", fontSize=8, fontName="Helvetica-Bold",
            textColor=colors.white, backColor=C_AI_HDR,
            leftIndent=8, spaceBefore=8, spaceAfter=0, leading=14,
        ),
        "p": ps(f"P{'H' if is_human else 'A'}",
                fontSize=10, leading=16, backColor=bg,
                leftIndent=10, rightIndent=6, spaceAfter=3),
        "h1": ps(f"H1{'H' if is_human else 'A'}",
                 fontSize=15, fontName="Helvetica-Bold", textColor=C_H1,
                 backColor=bg, leftIndent=10, spaceBefore=8, spaceAfter=3, leading=20),
        "h2": ps(f"H2{'H' if is_human else 'A'}",
                 fontSize=13, fontName="Helvetica-Bold", textColor=C_H2,
                 backColor=bg, leftIndent=10, spaceBefore=6, spaceAfter=2, leading=18),
        "h3": ps(f"H3{'H' if is_human else 'A'}",
                 fontSize=11, fontName="Helvetica-Bold", textColor=C_H3,
                 backColor=bg, leftIndent=10, spaceBefore=5, spaceAfter=2, leading=16),
        "li": ps(f"LI{'H' if is_human else 'A'}",
                 fontSize=10, leading=15, backColor=bg,
                 leftIndent=20, rightIndent=6, spaceAfter=2),
        "blockquote": ps(f"BQ{'H' if is_human else 'A'}",
                         fontSize=10, leading=15, fontName="Helvetica-Oblique",
                         textColor=colors.HexColor("#5D4037"),
                         backColor=C_QUOTE_BG, leftIndent=18, rightIndent=6, spaceAfter=4),
        "code_block": ParagraphStyle(
            "CodeBlock", parent=base["Code"],
            fontSize=8.5, leading=13, fontName="Courier",
            textColor=C_CODE_FG, backColor=C_CODE_BG,
            leftIndent=10, rightIndent=6, spaceBefore=4, spaceAfter=6,
        ),
        "bubble_end": ps(f"BEnd{'H' if is_human else 'A'}",
                         fontSize=2, leading=2, backColor=bg, spaceAfter=4),
        "field_key": ps("FieldKey", fontSize=9, fontName="Helvetica-Bold",
                        textColor=colors.HexColor("#333333")),
        "field_val": ps("FieldVal", fontSize=9, leading=13,
                        textColor=colors.HexColor("#1A1A1A")),
    }


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _inline(text: str) -> str:
    """Convert inline Markdown to ReportLab XML inline markup."""
    # Strip any raw HTML
    text = re.sub(r'<[^>]+>', '', text)
    text = _escape(text)
    # Bold+italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_([^_\s][^_]*)_', r'<i>\1</i>', text)
    # Inline code  `code`
    text = re.sub(
        r'`([^`]+)`',
        r'<font name="Courier" color="#B71C1C" backColor="#FCE4EC"> \1 </font>',
        text,
    )
    # Strikethrough
    text = re.sub(r'~~(.+?)~~', r'<strike>\1</strike>', text)
    return text


def _md_to_flowables(md_text: str, styles: dict) -> list:
    """
    Parse markdown line-by-line into ReportLab flowables.
    Each flowable is emitted individually so ReportLab can paginate freely.
    """
    flowables = []
    lines = md_text.split("\n")
    i = 0
    in_code = False
    code_lines: list = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── Fenced code block ─────────────────────────────────────────────
        fence_match = re.match(r'^```', stripped)
        if fence_match:
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                code_text = "\n".join(code_lines) if code_lines else " "
                flowables.append(Preformatted(code_text, styles["code_block"]))
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # ── Blank line ────────────────────────────────────────────────────
        if stripped == "":
            flowables.append(Spacer(1, 5))
            i += 1
            continue

        # ── Heading ###### ────────────────────────────────────────────────
        m = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if m:
            level = len(m.group(1))
            key = "h1" if level == 1 else "h2" if level == 2 else "h3"
            flowables.append(Paragraph(_inline(m.group(2)), styles[key]))
            i += 1
            continue

        # ── Horizontal rule ───────────────────────────────────────────────
        if re.match(r'^[-*_]{3,}$', stripped):
            flowables.append(
                HRFlowable(width="95%", thickness=0.5, color=C_BORDER,
                           spaceBefore=3, spaceAfter=3)
            )
            i += 1
            continue

        # ── Blockquote ────────────────────────────────────────────────────
        if stripped.startswith("> "):
            flowables.append(
                Paragraph(_inline(stripped[2:]), styles["blockquote"])
            )
            i += 1
            continue

        # ── Unordered list ────────────────────────────────────────────────
        if re.match(r'^[-*+]\s+', stripped):
            items = []
            while i < len(lines):
                ls = lines[i].strip()
                if re.match(r'^[-*+]\s+', ls):
                    txt = re.sub(r'^[-*+]\s+', '', ls)
                    items.append(
                        ListItem(
                            Paragraph(_inline(txt), styles["li"]),
                            bulletColor=C_ACCENT,
                        )
                    )
                    i += 1
                else:
                    break
            flowables.append(
                ListFlowable(items, bulletType="bullet",
                             leftIndent=12, bulletFontSize=8)
            )
            continue

        # ── Ordered list ──────────────────────────────────────────────────
        if re.match(r'^\d+[.)]\s+', stripped):
            items = []
            num = 1
            while i < len(lines):
                ls = lines[i].strip()
                if re.match(r'^\d+[.)]\s+', ls):
                    txt = re.sub(r'^\d+[.)]\s+', '', ls)
                    items.append(
                        ListItem(
                            Paragraph(_inline(txt), styles["li"]),
                            value=num,
                        )
                    )
                    num += 1
                    i += 1
                else:
                    break
            flowables.append(
                ListFlowable(items, bulletType="1",
                             leftIndent=12, bulletFontSize=9)
            )
            continue

        # ── Normal paragraph ──────────────────────────────────────────────
        flowables.append(Paragraph(_inline(stripped), styles["p"]))
        i += 1

    return flowables


def _message_block(msg: Dict[str, Any]) -> list:
    """Render one chat message as individual flowables (no KeepTogether)."""
    is_human = msg.get("type") == "human"
    raw = (msg.get("content") or "").strip()
    styles = _build_styles(is_human=is_human)

    label_style = styles["human_label"] if is_human else styles["ai_label"]
    label_text = "  Human" if is_human else "  AI Assistant"

    flowables = [Paragraph(label_text, label_style)]
    flowables.extend(_md_to_flowables(raw, styles))
    flowables.append(Paragraph("", styles["bubble_end"]))
    return flowables


def generate_session_report_pdf(
    session_id: str,
    history: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
) -> bytes:
    """
    Generate a Markdown-aware, properly paginated PDF session report.

    Markdown in messages is fully rendered:
      headings, **bold**, *italic*, `inline code`, code blocks,
      - unordered lists, 1. ordered lists, > blockquotes, --- rules

    Human messages: green header bar + light-green background.
    AI messages:    blue header bar  + light-grey background.

    No KeepTogether wrapping — messages paginate freely.
    """
    buffer = BytesIO()
    LEFT = RIGHT = 48
    TOP  = BOT   = 40

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=RIGHT, leftMargin=LEFT,
        topMargin=TOP, bottomMargin=BOT,
    )
    page_w = letter[0] - LEFT - RIGHT
    base   = getSampleStyleSheet()
    _s     = _build_styles(is_human=False)
    flow   = []

    # ── Title ──────────────────────────────────────────────────────────────
    flow.append(Paragraph("Session Report", _s["report_title"]))
    flow.append(Paragraph(f"Session ID: {_escape(session_id)}", _s["session_id"]))
    flow.append(Spacer(1, 6))
    flow.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT, spaceAfter=12))

    # ── Conversation ───────────────────────────────────────────────────────
    flow.append(Paragraph("Conversation History", _s["section_heading"]))
    flow.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=6))

    if not history:
        flow.append(Paragraph("No conversation history available.", base["Normal"]))
    else:
        for msg in history:
            flow.extend(_message_block(msg))

    flow.append(Spacer(1, 16))
    flow.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=8))

    # ── Artifacts ──────────────────────────────────────────────────────────
    flow.append(Paragraph("Structured Artifacts", _s["section_heading"]))
    flow.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=6))

    if not artifacts:
        flow.append(Paragraph("No artifacts recorded for this session.", base["Normal"]))
    else:
        for art in artifacts:
            title_text = art.get("intent") or art.get("type") or "Artifact"
            flow.append(Paragraph(f"▸ {_escape(str(title_text))}", _s["section_heading"]))

            keys = [k for k in art.keys() if k != "tool_calls"]
            rows = []
            for k in keys:
                v = art.get(k)
                try:
                    val_text = str(v)
                except Exception:
                    val_text = "<unserializable>"
                rows.append([
                    Paragraph(_escape(str(k)), _s["field_key"]),
                    Paragraph(_escape(val_text), _s["field_val"]),
                ])

            if rows:
                tbl = Table(rows,
                            colWidths=[page_w * 0.25, page_w * 0.75],
                            splitByRow=True)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#F1F3F4")),
                    ("BACKGROUND",    (1, 0), (1, -1), colors.white),
                    ("GRID",          (0, 0), (-1, -1), 0.25, C_BORDER),
                    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING",    (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                    *[
                        ("BACKGROUND", (1, i), (1, i), colors.HexColor("#FAFAFA"))
                        for i in range(0, len(rows), 2)
                    ],
                ]))
                flow.append(tbl)
                flow.append(Spacer(1, 10))

    doc.build(flow)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
