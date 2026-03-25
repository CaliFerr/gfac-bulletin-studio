from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .data import BulletinSection, ProgramEntry, iter_extra_lines, load_bulletin_sections


PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 0.45 * inch
RIGHT_MARGIN = 0.45 * inch
TOP_MARGIN = 0.42 * inch
BOTTOM_MARGIN = 0.45 * inch
COLUMN_GAP = 0.52 * inch
COLUMN_WIDTH = (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - COLUMN_GAP) / 2

HEADER_HEIGHT = 0.58 * inch
SECTION_TOP_GAP = 0.30 * inch
ROW_GAP = 0.07 * inch

INK = HexColor("#2A2622")
MUTED = HexColor("#5E554D")
PANEL_FILL = HexColor("#D9D9D9")
PANEL_STROKE = HexColor("#595959")


def build_bulletin_pdf(csv_or_sections: str | Path | list[BulletinSection], output_path: str | Path) -> Path:
    """Render the fixed three-section bulletin layout from the CSV structure."""

    if isinstance(csv_or_sections, (str, Path)):
        sections = load_bulletin_sections(csv_or_sections)
    else:
        sections = csv_or_sections

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output), pagesize=letter)

    _draw_program_page(pdf, sections)
    pdf.showPage()

    pdf.save()
    return output


def _draw_program_page(pdf: canvas.Canvas, sections: list[BulletinSection]) -> None:
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

    left_x = LEFT_MARGIN
    right_x = LEFT_MARGIN + COLUMN_WIDTH + COLUMN_GAP
    top_y = PAGE_HEIGHT - TOP_MARGIN

    by_title = {section.title.lower(): section for section in sections}
    filipino = by_title.get("filipino service")
    sabbath = by_title.get("sabbath school")
    worship = by_title.get("hour of worship")

    left_cursor = top_y
    if filipino is not None:
        left_cursor = _draw_section(pdf, filipino, left_x, left_cursor)
    if sabbath is not None:
        left_cursor -= 0.28 * inch
        _draw_section(pdf, sabbath, left_x, left_cursor)

    if worship is not None:
        _draw_section(pdf, worship, right_x, top_y)


def _draw_section(pdf: canvas.Canvas, section: BulletinSection, x: float, top_y: float) -> float:
    _draw_header(pdf, x, top_y, section.title, section.time)
    cursor_y = top_y - HEADER_HEIGHT - SECTION_TOP_GAP
    for entry in section.entries:
        cursor_y = _draw_entry(pdf, entry, x, cursor_y)
    return cursor_y


def _draw_header(pdf: canvas.Canvas, x: float, top_y: float, title: str, time_text: str) -> None:
    pdf.setFillColor(PANEL_FILL)
    pdf.setStrokeColor(PANEL_STROKE)
    pdf.roundRect(x, top_y - HEADER_HEIGHT, COLUMN_WIDTH, HEADER_HEIGHT, 10, fill=1, stroke=1)

    baseline = top_y - 0.35 * inch

    pdf.setFillColor(INK)
    pdf.setFont("Times-Bold", 16)
    pdf.drawString(x + 0.06 * inch, baseline, title)

    pdf.setFont("Times-Bold", 15)
    pdf.drawRightString(x + COLUMN_WIDTH - 0.06 * inch, baseline, time_text)


def _draw_entry(pdf: canvas.Canvas, entry: ProgramEntry, x: float, top_y: float) -> float:
    title_x = x + 0.03 * inch
    name_x = x + COLUMN_WIDTH - 0.03 * inch
    cursor_y = top_y

    pdf.setFillColor(INK)
    pdf.setFont("Times-Roman", 11)
    pdf.drawString(title_x, cursor_y, entry.title)

    if entry.name:
        pdf.setFont("Times-Roman", 11)
        pdf.drawRightString(name_x, cursor_y, entry.name)

    cursor_y -= 0.17 * inch

    extra_lines = list(iter_extra_lines(entry.extra))
    if extra_lines:
        pdf.setFillColor(MUTED)
        pdf.setFont("Times-Italic", 10)
        center_x = x + (COLUMN_WIDTH / 2)
        for line in extra_lines:
            pdf.drawCentredString(center_x, cursor_y, line)
            cursor_y -= 0.14 * inch

    return cursor_y - ROW_GAP
