from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .data import load_bulletin_sections
from .paths import assets_dir


ASSETS_DIR = assets_dir()
BACKGROUND_IMAGE = ASSETS_DIR / "lower_third_background.png"
LOGO_IMAGE = ASSETS_DIR / "gfac_logo_white.png"
HORIZON_FONT = ASSETS_DIR / "Horizon.otf"
HORIZON_OUTLINED_FONT = ASSETS_DIR / "Horizon_Outlined.otf"
HORIZON_FONT_ALT = ASSETS_DIR / "Horizon.ttf"
PRIMARY_FONT = ASSETS_DIR / "Montserrat-ExtraBold.ttf"
PRIMARY_FONT_ALT = ASSETS_DIR / "Arial Bold.ttf"

CANVAS_SIZE = (1920, 1080)
BANNER_X = 0
BANNER_Y = 900
BANNER_WIDTH = 1920
BANNER_HEIGHT = 112
TEXT_LEFT_PADDING = 180
TEXT_RIGHT_PADDING = 260


@dataclass(frozen=True)
class LowerThirdItem:
    filename: str
    background_word: str
    primary_text: str
    secondary_text: str


def export_lower_thirds(csv_path: str | Path, output_dir: str | Path) -> list[Path]:
    sections = load_bulletin_sections(csv_path)
    items = _build_items(sections)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    for item in items:
        image = _render_lower_third(item)
        target = output / f"{item.filename}.png"
        image.save(target)
        exported.append(target)
    return exported


def _build_items(sections) -> list[LowerThirdItem]:
    items: list[LowerThirdItem] = []
    for section in sections:
        background_word = _background_word_for_section(section.title)
        for entry in section.entries:
            primary, secondary = _resolve_text(entry.title, entry.name, entry.extra)
            if not primary:
                continue

            items.append(
                LowerThirdItem(
                    filename=_slugify(f"{section.title}_{entry.title}_{entry.name or entry.extra or primary}"),
                    background_word=background_word,
                    primary_text=primary,
                    secondary_text=secondary,
                )
            )
    return items


def _resolve_text(title: str, name: str, extra: str) -> tuple[str, str]:
    title_clean = title.strip()
    name_clean = name.strip()
    extra_clean = extra.strip()
    title_lower = title_clean.lower()
    name_lower = name_clean.lower()

    music_titles = {
        "special music",
        "special number",
        "prelude",
        "offertory",
        "postlude",
        "opening song",
        "song of consecration",
        "awit ng pagpuri",
        "awit sa pagtatapos",
        "tanging bilang",
    }
    if title_lower in music_titles:
        primary = extra_clean or name_clean or title_clean
        performers = name_clean if extra_clean and name_clean else ""
        secondary = title_clean.upper()
        if performers:
            secondary = f"{secondary} [{performers.upper()}]"
        return primary.upper(), secondary

    if name_clean:
        return name_clean.upper(), title_clean.upper()

    if extra_clean:
        return extra_clean.upper(), title_clean.upper()

    return title_clean.upper(), ""


def _background_word_for_section(section_title: str) -> str:
    mapping = {
        "Filipino Service": "FILIPINO SERVICE",
        "Sabbath School": "SABBATH SCHOOL",
        "Hour Of Worship": "HOUR OF WORSHIP",
    }
    return mapping.get(section_title, section_title.upper())


def _render_lower_third(item: LowerThirdItem) -> Image.Image:
    image = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    banner = _build_banner_background()
    image.alpha_composite(banner, (BANNER_X, BANNER_Y))

    draw = ImageDraw.Draw(image)
    _draw_background_word(draw, item.background_word)
    _draw_primary_text(draw, item.primary_text)
    _draw_secondary_text(draw, item.secondary_text)
    _draw_logo(draw, image)
    return image


def _build_banner_background() -> Image.Image:
    if BACKGROUND_IMAGE.exists():
        banner = Image.open(BACKGROUND_IMAGE).convert("RGBA")
        if banner.size != (BANNER_WIDTH, BANNER_HEIGHT):
            banner = banner.resize((BANNER_WIDTH, BANNER_HEIGHT), Image.Resampling.LANCZOS)
    else:
        banner = Image.new("RGBA", (BANNER_WIDTH, BANNER_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(banner)
        left = (120, 210, 245)
        right = (50, 173, 232)
        for x in range(BANNER_WIDTH):
            mix = x / max(1, BANNER_WIDTH - 1)
            color = tuple(int(left[i] + ((right[i] - left[i]) * mix)) for i in range(3))
            draw.line((x, 0, x, BANNER_HEIGHT), fill=color + (240,), width=1)

    return banner


def _draw_background_word(draw: ImageDraw.ImageDraw, background_word: str) -> None:
    font = _fit_font(draw, background_word, 122, 1420, bold=True, role="horizon")
    bbox = draw.textbbox((0, 0), background_word, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = _content_center_x(width)
    y = BANNER_Y + ((BANNER_HEIGHT - height) // 2) - 2
    fill = (255, 255, 255, 220) if HORIZON_OUTLINED_FONT.exists() else (255, 255, 255, 0)
    draw.text((x, y), background_word, font=font, fill=fill)


def _draw_primary_text(draw: ImageDraw.ImageDraw, text: str) -> None:
    font = _fit_font(draw, text, 56, 780, bold=True, role="horizon_filled")
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = _content_center_x(width)
    block_top = BANNER_Y + 10
    draw.text((x, block_top), text, font=font, fill=(255, 255, 255, 255))


def _draw_secondary_text(draw: ImageDraw.ImageDraw, text: str) -> None:
    if not text:
        return

    font = _fit_font(draw, text, 32, 760, bold=True, role="primary")
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = _content_center_x(width)
    y = BANNER_Y + 60
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))


def _draw_logo(draw: ImageDraw.ImageDraw, image: Image.Image) -> None:
    if LOGO_IMAGE.exists():
        logo = Image.open(LOGO_IMAGE).convert("RGBA")
        logo.thumbnail((280, 122), Image.Resampling.LANCZOS)
        x = BANNER_X + BANNER_WIDTH - logo.width - 10
        y = BANNER_Y + max(0, (BANNER_HEIGHT - logo.height) // 2)
        image.alpha_composite(logo, (x, y))
        return

    font = _font(54, bold=True, role="primary")
    draw.text((1660, BANNER_Y + 14), "GFAC", font=font, fill=(255, 255, 255, 255))


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    start_size: int,
    max_width: int,
    bold: bool = False,
    role: str = "primary",
) -> ImageFont.FreeTypeFont:
    size = start_size
    while size > 16:
        font = _font(size, bold=bold, role=role)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            return font
        size -= 2
    return _font(16, bold=bold, role=role)


def _font(size: int, bold: bool = False, role: str = "primary") -> ImageFont.FreeTypeFont:
    preferred_paths: list[Path] = []
    font_names: list[str] = []

    if role == "horizon":
        preferred_paths.extend([HORIZON_OUTLINED_FONT, HORIZON_FONT, HORIZON_FONT_ALT])
        font_names.extend(["Arial.ttf", "arial.ttf"])
    elif role == "horizon_filled":
        preferred_paths.extend([HORIZON_FONT, HORIZON_FONT_ALT])
        font_names.extend(["arialbd.ttf", "segoeuib.ttf"])
    else:
        preferred_paths.extend([PRIMARY_FONT, PRIMARY_FONT_ALT])
        if bold:
            font_names.extend(["arialbd.ttf", "segoeuib.ttf"])
        else:
            font_names.extend(["arial.ttf", "segoeui.ttf"])

    for path in preferred_paths:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)

    for name in font_names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "lower_third"


def _content_center_x(text_width: int) -> int:
    usable_left = TEXT_LEFT_PADDING
    usable_right = BANNER_WIDTH - TEXT_RIGHT_PADDING
    usable_width = usable_right - usable_left
    return usable_left + max(0, (usable_width - text_width) // 2)
