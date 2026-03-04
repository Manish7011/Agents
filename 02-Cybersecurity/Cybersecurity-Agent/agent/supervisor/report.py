from io import BytesIO
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def generate_session_report_pdf(session_id: str, history: List[Dict[str, Any]], artifacts: List[Dict[str, Any]]) -> bytes:
    """Generate a PDF bytes for a session report containing the chat history and artifacts.

    Args:
        session_id: session identifier
        history: list of message dicts {type: 'human'|'ai', content: str}
        artifacts: list of structured artifact dicts

    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    flow = []

    # Title
    flow.append(Paragraph(f"Session Report: {session_id}", styles["Title"]))
    flow.append(Spacer(1, 12))

    # History
    flow.append(Paragraph("Conversation History", styles["Heading2"]))
    flow.append(Spacer(1, 6))
    if not history:
        flow.append(Paragraph("No conversation history available.", styles["Normal"]))
    else:
        # Build a simple two-column table: speaker | content
        table_data = [["Speaker", "Message"]]
        for msg in history:
            speaker = "Human" if msg.get("type") == "human" else "AI"
            content = (msg.get("content") or "").replace("\n", " ")
            # Truncate long messages for the table, full text can be appended later
            table_data.append([speaker, content])

        tbl = Table(table_data, colWidths=[80, 420])
        tbl.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        flow.append(tbl)

    flow.append(Spacer(1, 12))

    # Artifacts
    flow.append(Paragraph("Structured Artifacts", styles["Heading2"]))
    flow.append(Spacer(1, 6))
    if not artifacts:
        flow.append(Paragraph("No artifacts recorded for this session.", styles["Normal"]))
    else:
        # For each artifact, print a small table of key/value
        for art in artifacts:
            keys = [k for k in art.keys() if k != "tool_calls"]
            # Title row
            title = art.get("intent") or art.get("type") or "Artifact"
            flow.append(Paragraph(f"- {title}", styles["Heading4"]))
            rows = [["Field", "Value"]]
            for k in keys:
                v = art.get(k)
                # Try stringify
                try:
                    val_text = str(v)
                except Exception:
                    val_text = "<unserializable>"
                rows.append([str(k), val_text])
            t = Table(rows, colWidths=[140, 360])
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f8f8")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            flow.append(t)
            flow.append(Spacer(1, 8))

    # Build PDF
    doc.build(flow)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

