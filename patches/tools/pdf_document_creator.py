"""
title: PDF Document Creator
author: AI Stack
description: >
  Creates professional PDF documents from structured content.
  Supports headings, paragraphs, bullet lists, and tables.
  Registers the file with Open WebUI and returns a proper download link.
version: 3.1.0
requirements: reportlab
"""

import os
import re
import tempfile
import httpx
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER


# ---------------------------------------------------------------------------
# Module-level helpers — NOT class methods, so they are excluded from the
# tool specs that Open WebUI generates (dir(Tools()) only returns class attrs).
# ---------------------------------------------------------------------------

def _get_public_base_url(webui_base_url: str, request) -> str:
    """URL for user-facing download links: valve > request.base_url > fallback."""
    if webui_base_url:
        return webui_base_url.rstrip("/")
    if request and hasattr(request, "base_url"):
        return str(request.base_url).rstrip("/")
    return "http://localhost:8080"


def _get_token(request) -> str:
    if request and hasattr(request, "headers"):
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
    return ""


async def _upload_file(file_path: str, filename: str, token: str) -> str:
    if not token:
        raise ValueError(
            "No Bearer token found in request. "
            "Check that __request__ is declared in the function signature."
        )
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            resp = await client.post(
                "http://localhost:8080/api/v1/files/",
                headers=headers,
                files={"file": (filename, f, "application/pdf")},
                params={"process": "false"},
                timeout=60,
            )
    resp.raise_for_status()
    return resp.json()["id"]


def _build_pdf_styles():
    styles = getSampleStyleSheet()
    return {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1F4E79"),
            spaceAfter=20,
            alignment=TA_CENTER,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#1F4E79"),
            spaceBefore=16,
            spaceAfter=6,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#2E75B6"),
            spaceBefore=12,
            spaceAfter=4,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=styles["Heading3"],
            fontSize=11,
            textColor=colors.HexColor("#404040"),
            spaceBefore=8,
            spaceAfter=2,
        ),
        "Body": ParagraphStyle(
            "Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=20,
            spaceAfter=3,
            bulletIndent=10,
        ),
    }


# ---------------------------------------------------------------------------
# Tool class — only create_pdf is exposed as a callable spec.
# ---------------------------------------------------------------------------

class Tools:
    class Valves(BaseModel):
        WEBUI_BASE_URL: str = Field(
            default="",
            description=(
                "Public-facing Open WebUI URL users access in their browser "
                "(e.g. http://192.168.1.100:8089). Leave blank to auto-detect from the request."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

    async def create_pdf(
        self,
        filename: str,
        title: str,
        content: str,
        page_size: str = "LETTER",
        __request__=None,
        __event_emitter__=None,
    ) -> str:
        """
        Create a formatted PDF document from markdown-like content.

        :param filename: Output filename without extension (e.g. 'project_proposal')
        :param title: Document title displayed at the top
        :param content: Document content using markdown-like syntax:
                        - '# ' → Heading 1, '## ' → Heading 2, '### ' → Heading 3
                        - '- ' or '* ' → Bullet point
                        - '| col | col |' → Table (first row = header)
                        - '---' → Horizontal divider
                        - '===' → Page break
                        - **text** → bold, *text* → italic
        :param page_size: 'LETTER' (US default) or 'A4' (international)
        :return: Download link and confirmation message
        """
        try:
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": "Building PDF...", "done": False}}
                )

            styles = _build_pdf_styles()
            page = LETTER if page_size.upper() == "LETTER" else A4

            safe_name = re.sub(r"[^\w\-]", "_", filename).strip("_")
            pdf_filename = f"{safe_name}.pdf"

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = tmp.name

            doc = SimpleDocTemplate(
                tmp_path,
                pagesize=page,
                rightMargin=1.25 * inch,
                leftMargin=1.25 * inch,
                topMargin=1 * inch,
                bottomMargin=1 * inch,
                title=title,
            )

            story = []
            story.append(Paragraph(title, styles["DocTitle"]))
            story.append(
                HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1F4E79"))
            )
            story.append(Spacer(1, 0.2 * inch))

            lines = content.split("\n")
            table_rows = []
            bullet_items = []

            def flush_bullets():
                for item in bullet_items:
                    story.append(Paragraph(f"• {item}", styles["Bullet"]))
                if bullet_items:
                    story.append(Spacer(1, 0.05 * inch))
                bullet_items.clear()

            def flush_table():
                if not table_rows:
                    return
                col_count = max(len(r) for r in table_rows)
                padded = [r + [""] * (col_count - len(r)) for r in table_rows]
                col_w = (6.5 * inch) / col_count
                t = Table(padded, colWidths=[col_w] * col_count)
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.HexColor("#EBF3FB"), colors.white],
                            ),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAAAAA")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(t)
                story.append(Spacer(1, 0.15 * inch))
                table_rows.clear()

            for line in lines:
                if line.startswith("# "):
                    flush_bullets()
                    flush_table()
                    story.append(Paragraph(line[2:].strip(), styles["H1"]))
                elif line.startswith("## "):
                    flush_bullets()
                    flush_table()
                    story.append(Paragraph(line[3:].strip(), styles["H2"]))
                elif line.startswith("### "):
                    flush_bullets()
                    flush_table()
                    story.append(Paragraph(line[4:].strip(), styles["H3"]))
                elif line.startswith("- ") or line.startswith("* "):
                    flush_table()
                    bullet_items.append(line[2:].strip())
                elif line.startswith("|"):
                    flush_bullets()
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    if not all(set(c) <= set("-| ") for c in cells):
                        table_rows.append(cells)
                elif line.strip() == "---":
                    flush_bullets()
                    flush_table()
                    story.append(
                        HRFlowable(
                            width="100%",
                            thickness=0.5,
                            color=colors.HexColor("#CCCCCC"),
                        )
                    )
                    story.append(Spacer(1, 0.1 * inch))
                elif line.strip() == "===":
                    flush_bullets()
                    flush_table()
                    story.append(PageBreak())
                elif line.strip():
                    flush_bullets()
                    flush_table()
                    formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line.strip())
                    formatted = re.sub(r"\*(.+?)\*", r"<i>\1</i>", formatted)
                    story.append(Paragraph(formatted, styles["Body"]))

            flush_bullets()
            flush_table()
            doc.build(story)

            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": "Uploading...", "done": False}}
                )

            public_url = _get_public_base_url(self.valves.WEBUI_BASE_URL, __request__)
            token = _get_token(__request__)
            file_id = await _upload_file(tmp_path, pdf_filename, token)
            os.unlink(tmp_path)

            download_url = f"{public_url}/api/v1/files/{file_id}/content/{pdf_filename}"

            if __event_emitter__:
                await __event_emitter__(
                    {"type": "status", "data": {"description": "Done", "done": True}}
                )
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": f"📥 **[Download {pdf_filename}]({download_url})**"},
                    }
                )

            return f"📥 [Download {pdf_filename}]({download_url})\n\nPDF created and uploaded. Include this exact download link verbatim in your response."

        except Exception as e:
            return f"❌ PDF creation failed: {str(e)}"
