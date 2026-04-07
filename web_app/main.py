from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from bulletin_app.bulletin_pdf import build_bulletin_pdf
from bulletin_app.data import load_bulletin_sections
from bulletin_app.lower_thirds import export_lower_thirds


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
WEB_OUTPUT_DIR = PROJECT_DIR / "web_output"
DIST_DIR = PROJECT_DIR / "dist"
WEB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SECTIONS = [
    ("Filipino Service", "9:00 am"),
    ("Sabbath School", "10:00 am"),
    ("Hour Of Worship", "11:15 am"),
]


class ProgramRowPayload(BaseModel):
    title: str = ""
    subheading: str = ""
    small_subheading: str = ""


class ProgramSectionPayload(BaseModel):
    title: str
    time: str
    rows: list[ProgramRowPayload] = Field(default_factory=list)


class ProgramPayload(BaseModel):
    sections: list[ProgramSectionPayload]


app = FastAPI(title="GFAC Bulletin Studio Web")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.get("/api/default-program")
def default_program() -> dict[str, object]:
    return {"sections": _empty_sections()}


@app.post("/api/import-csv")
async def import_csv(file: UploadFile = File(...)) -> dict[str, object]:
    suffix = Path(file.filename or "program.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        temp_path = Path(handle.name)
        handle.write(await file.read())

    try:
        sections = load_bulletin_sections(temp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)

    serialized = []
    for section in sections:
        serialized.append(
            {
                "title": section.title,
                "time": section.time,
                "rows": [
                    {
                        "title": entry.title,
                        "subheading": entry.name,
                        "small_subheading": entry.extra,
                    }
                    for entry in section.entries
                ],
            }
        )

    return {"sections": serialized}


@app.post("/api/export/csv")
def export_csv(payload: ProgramPayload) -> FileResponse:
    csv_path = _write_payload_csv(payload, WEB_OUTPUT_DIR / "program_web.csv")
    return FileResponse(csv_path, media_type="text/csv", filename="program_web.csv")


@app.post("/api/export/bulletin")
def export_bulletin(payload: ProgramPayload) -> FileResponse:
    csv_path = _write_payload_csv(payload, WEB_OUTPUT_DIR / "program_web.csv")
    pdf_path = WEB_OUTPUT_DIR / "program_web_bulletin.pdf"
    build_bulletin_pdf(csv_path, pdf_path)
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)


@app.post("/api/export/lower-thirds")
def export_lower_thirds_zip(payload: ProgramPayload) -> FileResponse:
    csv_path = _write_payload_csv(payload, WEB_OUTPUT_DIR / "program_web.csv")
    output_dir = WEB_OUTPUT_DIR / "lower_thirds"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    exported = export_lower_thirds(csv_path, output_dir)
    zip_path = WEB_OUTPUT_DIR / "lower_thirds_web.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in exported:
            archive.write(file_path, arcname=file_path.name)
    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


@app.get("/api/download/desktop")
def download_desktop() -> FileResponse:
    onefile_path = DIST_DIR / "GFAC Bulletin Studio.exe"
    folder_path = DIST_DIR / "GFAC Bulletin Studio"

    if onefile_path.exists():
        return FileResponse(
            onefile_path,
            media_type="application/vnd.microsoft.portable-executable",
            filename=onefile_path.name,
        )

    if folder_path.exists() and folder_path.is_dir():
        zip_path = WEB_OUTPUT_DIR / "GFAC Bulletin Studio Desktop.zip"
        if zip_path.exists():
            zip_path.unlink()
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, arcname=file_path.relative_to(folder_path.parent))
        return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)

    raise HTTPException(
        status_code=404,
        detail="Desktop build not found. Run build_onefile.ps1 or build.ps1 first.",
    )


def _empty_sections() -> list[dict[str, object]]:
    return [
        {"title": title, "time": time_text, "rows": [{"title": "", "subheading": "", "small_subheading": ""}]}
        for title, time_text in DEFAULT_SECTIONS
    ]


def _write_payload_csv(payload: ProgramPayload, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = _payload_to_rows(payload)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["title", "subheading", "small_subheading"])
        writer.writeheader()
        writer.writerows(rows)
    return target


def _payload_to_rows(payload: ProgramPayload) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for section in payload.sections:
        rows.append(
            {
                "title": section.title.strip(),
                "subheading": section.time.strip(),
                "small_subheading": "",
            }
        )
        for row in section.rows:
            if not any((row.title.strip(), row.subheading.strip(), row.small_subheading.strip())):
                continue
            rows.append(
                {
                    "title": row.title,
                    "subheading": row.subheading,
                    "small_subheading": row.small_subheading,
                }
            )
    return rows
