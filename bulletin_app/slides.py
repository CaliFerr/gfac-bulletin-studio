from __future__ import annotations

import os
import shutil
from pathlib import Path

from .data import load_program_entries, read_csv_rows
from .paths import templates_dir, thumbnails_dir


IMAGE_SENTINEL = "[imported_image]"
TEMPLATES_DIR = templates_dir()
THUMBNAILS_DIR = thumbnails_dir()


def generate_slides(template_path: str | Path, csv_path: str | Path, output_path: str | Path) -> Path:
    """Generate a PowerPoint deck from a template and CSV data."""

    try:
        import comtypes.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("comtypes is required to generate PowerPoint slides on Windows.") from exc

    template = Path(template_path)
    csv_file = Path(csv_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template, output)

    app = comtypes.client.CreateObject("PowerPoint.Application")
    app.Visible = True

    presentation = None
    try:
        presentation = app.Presentations.Open(os.path.abspath(str(output)))
        opening_slide = presentation.Slides(1)
        template_slide = presentation.Slides(2)
        closing_slide = presentation.Slides(3)

        canonical_entries = load_program_entries(csv_file)
        raw_rows = read_csv_rows(csv_file)
        slide_rows = _build_slide_rows(canonical_entries, raw_rows)

        for row in slide_rows:
            new_slide = template_slide.Duplicate()
            if row["title"].strip() == IMAGE_SENTINEL:
                _insert_centered_image(new_slide, presentation, row["image_path"])
                continue

            for shape in new_slide.Shapes:
                if not shape.HasTextFrame:
                    continue

                text = shape.TextFrame.TextRange.Text
                text = text.replace("[Title]", row["title"])
                text = text.replace("[Subheading]", row["subheading"])
                text = text.replace("[Smaller Subheading]", row["small_subheading"])
                shape.TextFrame.TextRange.Text = text

        template_slide.Delete()
        closing_slide.MoveTo(len(presentation.Slides))
        presentation.Save()
        opening_slide.Select()
    finally:
        if presentation is not None:
            presentation.Close()
        app.Quit()

    return output


def list_templates() -> list[Path]:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(TEMPLATES_DIR.glob("*.pptx"))


def import_template(template_path: str | Path) -> Path:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(template_path)
    destination = TEMPLATES_DIR / source.name
    counter = 2

    while destination.exists():
        destination = TEMPLATES_DIR / f"{source.stem}_{counter}{source.suffix}"
        counter += 1

    shutil.copy2(source, destination)
    return destination


def ensure_thumbnail(template_path: str | Path) -> Path | None:
    template = Path(template_path)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail = THUMBNAILS_DIR / f"{template.stem}.png"

    if thumbnail.exists() and thumbnail.stat().st_mtime >= template.stat().st_mtime:
        return thumbnail

    try:
        import comtypes.client  # type: ignore
    except ImportError:
        return None

    try:
        app = comtypes.client.CreateObject("PowerPoint.Application")
    except Exception:
        return None

    presentation = None
    try:
        presentation = app.Presentations.Open(os.path.abspath(str(template)), WithWindow=False)
        presentation.Slides(1).Export(str(thumbnail), "PNG", 360, 202)
        return thumbnail if thumbnail.exists() else None
    except Exception:
        return None
    finally:
        if presentation is not None:
            presentation.Close()
        app.Quit()


def _build_slide_rows(canonical_entries, raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    image_rows = []
    for row in raw_rows:
        title = (row.get("title") or row.get("Title") or "").strip()
        if title == IMAGE_SENTINEL:
            image_rows.append(
                {
                    "title": IMAGE_SENTINEL,
                    "subheading": "",
                    "small_subheading": "",
                    "image_path": (row.get("image_path") or row.get("subheading") or "").strip(),
                }
            )

    content_rows = [
        {
            "title": entry.title,
            "subheading": entry.name,
            "small_subheading": entry.extra,
            "image_path": "",
        }
        for entry in canonical_entries
    ]
    return content_rows + image_rows


def _insert_centered_image(slide, presentation, image_path: str) -> None:
    if not image_path:
        return

    picture = slide.Shapes.AddPicture(
        FileName=os.path.abspath(image_path),
        LinkToFile=False,
        SaveWithDocument=True,
        Left=0,
        Top=0,
        Width=-1,
        Height=-1,
    )

    slide_width = presentation.PageSetup.SlideWidth
    slide_height = presentation.PageSetup.SlideHeight
    picture.Left = (slide_width - picture.Width) / 2
    picture.Top = (slide_height - picture.Height) / 2
