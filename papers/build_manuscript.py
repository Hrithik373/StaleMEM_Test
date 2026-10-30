"""Build an IEEE-style, two-column manuscript PDF from manuscript.md."""
from __future__ import annotations

import re
import subprocess
import sys
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    Image,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "manuscript.md"
OUTPUT = ROOT / "manuscript.pdf"
FIGURE_SCRIPT = ROOT / "figures" / "generate_figures.py"
LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
COLUMN_GUTTER = 5 * mm
COLUMN_WIDTH = (LETTER[0] - LEFT_MARGIN - RIGHT_MARGIN - COLUMN_GUTTER) / 2
BLACK = colors.HexColor("#111111")
GRAY = colors.HexColor("#444444")
RULE = colors.HexColor("#777777")
PALE = colors.HexColor("#F3F3F3")


def register_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    paths = {
        "IEEE-Times": font_dir / "times.ttf",
        "IEEE-Times-Bold": font_dir / "timesbd.ttf",
        "IEEE-Times-Italic": font_dir / "timesi.ttf",
        "IEEE-Times-BoldItalic": font_dir / "timesbi.ttf",
    }
    if all(path.exists() for path in paths.values()):
        for name, path in paths.items():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "IEEE-Times", normal="IEEE-Times", bold="IEEE-Times-Bold",
            italic="IEEE-Times-Italic", boldItalic="IEEE-Times-BoldItalic",
        )
    else:
        pdfmetrics.registerFontFamily(
            "Times-Roman", normal="Times-Roman", bold="Times-Bold",
            italic="Times-Italic", boldItalic="Times-BoldItalic",
        )


register_fonts()
FONT = "IEEE-Times" if "IEEE-Times" in pdfmetrics.getRegisteredFontNames() else "Times-Roman"
BOLD = "IEEE-Times-Bold" if FONT == "IEEE-Times" else "Times-Bold"
ITALIC = "IEEE-Times-Italic" if FONT == "IEEE-Times" else "Times-Italic"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    "PaperTitle", fontName=FONT, fontSize=21, leading=24,
    textColor=BLACK, alignment=TA_CENTER, spaceAfter=2.5 * mm,
))
styles.add(ParagraphStyle(
    "PaperSubtitle", fontName=FONT, fontSize=12, leading=14,
    textColor=BLACK, alignment=TA_CENTER, spaceAfter=3 * mm,
))
styles.add(ParagraphStyle(
    "PaperMeta", fontName=FONT, fontSize=8.5, leading=10,
    textColor=BLACK, alignment=TA_CENTER, spaceAfter=1 * mm,
))
styles.add(ParagraphStyle(
    "Section", fontName=BOLD, fontSize=10, leading=12,
    textColor=BLACK, alignment=TA_CENTER, spaceBefore=6 * mm,
    spaceAfter=2.2 * mm, keepWithNext=True,
))
styles.add(ParagraphStyle(
    "Subsection", fontName=ITALIC, fontSize=9.5, leading=11,
    textColor=BLACK, alignment=TA_LEFT, spaceBefore=3.2 * mm,
    spaceAfter=1.2 * mm, keepWithNext=True,
))
styles.add(ParagraphStyle(
    "BodyPaper", fontName=FONT, fontSize=10, leading=11.5,
    textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=1.8 * mm,
    splitLongWords=False, allowWidows=0, allowOrphans=0,
))
styles.add(ParagraphStyle(
    "AbstractPaper", fontName=ITALIC, fontSize=9, leading=10.5,
    textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=1.7 * mm,
    splitLongWords=False,
))
styles.add(ParagraphStyle(
    "AbstractHeading", fontName=BOLD, fontSize=9.2, leading=11,
    textColor=BLACK, alignment=TA_CENTER, spaceBefore=1 * mm,
    spaceAfter=1 * mm,
))
styles.add(ParagraphStyle(
    "IndexTerms", fontName=FONT, fontSize=8.3, leading=10,
    textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=2.5 * mm,
))
styles.add(ParagraphStyle(
    "TableCell", fontName=FONT, fontSize=7.2, leading=8.5,
    textColor=BLACK, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "TableHead", fontName=BOLD, fontSize=7.1, leading=8.3,
    textColor=BLACK, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "CaptionPaper", fontName=FONT, fontSize=8, leading=9.2,
    textColor=BLACK, alignment=TA_LEFT, spaceBefore=1 * mm,
    spaceAfter=2.5 * mm,
))
styles.add(ParagraphStyle(
    "QuotePaper", parent=styles["BodyPaper"], leftIndent=4 * mm,
    rightIndent=4 * mm, fontName=ITALIC,
))
styles.add(ParagraphStyle(
    "ReferencePaper", parent=styles["BodyPaper"], fontSize=8.5,
    leading=9.8, leftIndent=4.2 * mm, firstLineIndent=-4.2 * mm,
    spaceAfter=1.3 * mm,
))
styles.add(ParagraphStyle(
    "ListPaper", parent=styles["BodyPaper"], leftIndent=4 * mm,
    firstLineIndent=-3.5 * mm, spaceAfter=1.2 * mm,
))


def inline_markup(text: str) -> str:
    text = escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", text)
    text = text.replace("\\(", "(").replace("\\)", ")")
    text = text.replace("\\approx", "approximately ")
    return text


def section_heading(text: str) -> str:
    match = re.match(r"^(\d+)\.\s+(.+)$", text)
    if not match:
        return text.upper()
    number, title = int(match.group(1)), match.group(2)
    roman = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
    prefix = roman[number - 1] if 0 < number <= len(roman) else str(number)
    return f"{prefix}. {title.upper()}"


def subsection_heading(text: str) -> str:
    match = re.match(r"^\d+\.(\d+)\s+(.+)$", text)
    if not match:
        return text
    letter_index = int(match.group(1)) - 1
    letter = chr(ord("A") + letter_index) if 0 <= letter_index < 26 else str(letter_index + 1)
    return f"{letter}. {match.group(2)}"


def make_table(lines: list[str], width: float) -> Table:
    raw_rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
    ]
    rows = [row for row in raw_rows if not all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in row
    )]
    ncols = max(map(len, rows))
    col_widths = [width / ncols] * ncols
    if ncols == 4:
        col_widths = [width * 0.18, width * 0.13, width * 0.2, width * 0.49]
    cells = []
    for row_index, row in enumerate(rows):
        row += [""] * (ncols - len(row))
        cell_style = styles["TableHead"] if row_index == 0 else styles["TableCell"]
        cells.append([Paragraph(inline_markup(cell), cell_style) for cell in row])
    table = Table(cells, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, BLACK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.65, BLACK),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, BLACK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def parse_markdown(markdown: str) -> tuple[list, list]:
    lines = markdown.splitlines()
    title = ""
    subtitle = ""
    metadata: list[str] = []
    abstract: list[str] = []
    index_terms = ""
    body_start = None
    in_abstract = False

    for i, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## ") and title and not subtitle:
            subtitle = line[3:].strip()
        elif line.startswith("**Research manuscript"):
            metadata.append(line.replace("**", "").replace("—", "-").strip())
        elif line.startswith("**Authors:**") or line.startswith("**Affiliations:**") or line.startswith("**Corresponding author:**"):
            metadata.append(line.replace("**", "").strip())
        elif line == "## Abstract":
            in_abstract = True
        elif line.startswith("## 1. Introduction"):
            body_start = i
            break
        elif in_abstract and line.startswith("**Index Terms"):
            index_terms = line.replace("**", "").strip()
        elif in_abstract and line:
            abstract.append(line)

    if body_start is None:
        raise ValueError("Could not locate the manuscript introduction")

    title_story = [
        Spacer(1, 1.5 * mm),
        Paragraph(inline_markup(title), styles["PaperTitle"]),
        Paragraph(inline_markup(subtitle), styles["PaperSubtitle"]),
    ]
    title_story.extend(Paragraph(inline_markup(item), styles["PaperMeta"]) for item in metadata)
    title_story.append(Spacer(1, 1.5 * mm))

    body_story: list = [
        Paragraph("Abstract—", styles["AbstractHeading"]),
        Paragraph(inline_markup(" ".join(abstract)), styles["AbstractPaper"]),
        Paragraph(
            re.sub(r"^Index Terms—", "<i>Index Terms—</i>", inline_markup(index_terms)),
            styles["IndexTerms"],
        ),
    ]
    body_story.extend(parse_body(lines[body_start:]))
    return title_story, body_story


def parse_body(lines: list[str]) -> list:
    story: list = []
    body_lines: list[str] = []

    def flush_body() -> None:
        nonlocal body_lines
        text = " ".join(line.strip() for line in body_lines if line.strip())
        if text:
            style = styles["ReferencePaper"] if re.match(r"^\[\d+\]", text) else styles["BodyPaper"]
            story.append(Paragraph(inline_markup(text), style))
        body_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            flush_body()
            i += 1
            continue
        if line.startswith("## "):
            flush_body()
            heading = section_heading(line[3:].strip())
            story.append(Paragraph(inline_markup(heading), styles["Section"]))
            i += 1
            continue
        if line.startswith("### "):
            flush_body()
            heading = subsection_heading(line[4:].strip())
            story.append(Paragraph(inline_markup(heading), styles["Subsection"]))
            i += 1
            continue
        if line.startswith("|"):
            flush_body()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            story.append(make_table(table_lines, COLUMN_WIDTH))
            story.append(Spacer(1, 1.5 * mm))
            continue
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        if image_match:
            flush_body()
            caption, image_ref = image_match.groups()
            image_path = (ROOT / image_ref).resolve()
            if not image_path.exists():
                raise FileNotFoundError(f"Manuscript figure not found: {image_path}")
            image = Image(str(image_path))
            max_width = COLUMN_WIDTH
            max_height = 78 * mm
            scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
            story.append(image)
            caption = re.sub(r"^Figure\s+(\d+)\.", r"Fig. \1.", caption)
            story.append(Paragraph(inline_markup(caption), styles["CaptionPaper"]))
            i += 1
            continue
        if line.startswith(">"):
            flush_body()
            story.append(Paragraph(inline_markup(line.lstrip("> ").strip()), styles["QuotePaper"]))
            i += 1
            continue
        if re.match(r"^\d+\.\s", line):
            flush_body()
            story.append(Paragraph(inline_markup(line), styles["ListPaper"]))
            i += 1
            continue
        if line.startswith("**TABLE"):
            flush_body()
            story.append(Paragraph(inline_markup(line), styles["CaptionPaper"]))
            i += 1
            continue
        body_lines.append(line)
        i += 1
    flush_body()
    return story


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(BLACK)
    canvas.drawCentredString(LETTER[0] / 2, 8 * mm, str(doc.page))
    canvas.restoreState()


def create_document() -> BaseDocTemplate:
    page_width, page_height = LETTER
    left_margin = LEFT_MARGIN
    right_margin = RIGHT_MARGIN
    top_margin = 0.75 * 72
    bottom_margin = 1.0 * 72
    gutter = COLUMN_GUTTER
    content_width = page_width - left_margin - right_margin
    title_height = 1.55 * 72
    title_bottom = page_height - top_margin - title_height
    column_top = title_bottom - 8
    column_height = column_top - bottom_margin

    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=LETTER,
        leftMargin=left_margin, rightMargin=right_margin,
        topMargin=top_margin, bottomMargin=bottom_margin,
        title="Can Long-Context Models Track Implicitly Changing User States?",
        author="Hrithik Ghosh",
        subject="IEEE-style preliminary reproduction on the STALE benchmark",
    )
    title_frame = Frame(
        left_margin, title_bottom, content_width, title_height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="title",
    )
    col1 = Frame(
        left_margin, bottom_margin, COLUMN_WIDTH, column_height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="first-col-left",
    )
    col2 = Frame(
        left_margin + COLUMN_WIDTH + gutter, bottom_margin,
        COLUMN_WIDTH, column_height, leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0, id="first-col-right",
    )
    regular_col_height = page_height - top_margin - bottom_margin
    regular_left = Frame(
        left_margin, bottom_margin, COLUMN_WIDTH, regular_col_height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="col-left",
    )
    regular_right = Frame(
        left_margin + COLUMN_WIDTH + gutter, bottom_margin,
        COLUMN_WIDTH, regular_col_height, leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0, id="col-right",
    )
    doc.addPageTemplates([
        PageTemplate(id="FirstPage", frames=[title_frame, col1, col2], onPage=draw_page),
        PageTemplate(id="TwoColumn", frames=[regular_left, regular_right], onPage=draw_page),
    ])
    return doc


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    subprocess.run([sys.executable, str(FIGURE_SCRIPT)], check=True, cwd=ROOT.parent)
    title_story, body_story = parse_markdown(SOURCE.read_text(encoding="utf-8"))
    story = [
        *title_story,
        NextPageTemplate("TwoColumn"),
        FrameBreak(),
        *body_story,
    ]
    doc = create_document()
    doc.build(story)
    print(f"Built {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
