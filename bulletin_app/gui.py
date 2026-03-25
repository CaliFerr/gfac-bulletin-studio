from __future__ import annotations

import csv
import customtkinter as ctk
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw

from .lower_thirds import export_lower_thirds
from .slides import ensure_thumbnail, generate_slides, import_template, list_templates


THEMES = {
    "light": {
        "window_bg": "#F7F1EA",
        "shell_bg": "#F3EBE2",
        "card_bg": "#FFFDFC",
        "text": "#1C1A18",
        "muted": "#746A62",
        "green": "#315F55",
        "green_hover": "#274E46",
        "green_soft": "#E6F0EC",
        "green_border": "#A4C1B5",
        "amber": "#B9723D",
        "amber_hover": "#9E6132",
        "amber_soft": "#F6E9DE",
        "amber_border": "#DAB396",
        "neutral": "#E7DDD2",
        "button_soft": "#E9DED0",
        "button_soft_hover": "#DCCDBB",
        "status_success": "#2D6A4F",
        "status_error": "#A04432",
        "blue": "#2E7EDB",
        "blue_hover": "#246BBC",
        "blue_soft": "#E4F0FF",
        "blue_border": "#A9C6EC",
    },
    "dark": {
        "window_bg": "#181614",
        "shell_bg": "#211D1A",
        "card_bg": "#24201D",
        "text": "#F3ECE4",
        "muted": "#B8AEA5",
        "green": "#4E877A",
        "green_hover": "#3F7065",
        "green_soft": "#24332F",
        "green_border": "#4D6F65",
        "amber": "#C98A54",
        "amber_hover": "#AE7443",
        "amber_soft": "#36281E",
        "amber_border": "#755438",
        "neutral": "#403730",
        "button_soft": "#37302A",
        "button_soft_hover": "#4A413A",
        "status_success": "#356B54",
        "status_error": "#8B4336",
        "blue": "#4B93EA",
        "blue_hover": "#3778C7",
        "blue_soft": "#1E2C3F",
        "blue_border": "#48678C",
    },
}


class BulletinApp:
    def __init__(self) -> None:
        self.theme_mode = "light"
        ctk.set_appearance_mode(self.theme_mode)

        self.root = ctk.CTk(fg_color=self.c("window_bg"))
        self.root.title("GFAC Bulletin Studio")
        self.root.geometry("980x700")
        self.root.minsize(920, 650)

        self.csv_path = tk.StringVar()
        self.pdf_output_path = tk.StringVar()
        self.template_path = tk.StringVar()
        self.slides_output_path = tk.StringVar()
        self.lower_thirds_output_dir = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose a CSV file to begin.")

        self.template_preview_image: ctk.CTkImage | None = None
        self.hero_image: ctk.CTkImage | None = None
        self.template_gallery_window: ctk.CTkToplevel | None = None
        self.program_maker_window: ProgramMakerWindow | None = None
        self.current_screen = "import"

        self._build_shell()
        self._show_import_screen()

    def c(self, key: str) -> str:
        return THEMES[self.theme_mode][key]

    def run(self) -> None:
        self.root.mainloop()

    def _build_shell(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self.content = ctk.CTkFrame(self.root, fg_color=self.c("window_bg"), corner_radius=0)
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.status_bar = ctk.CTkLabel(
            self.root,
            textvariable=self.status_text,
            anchor="w",
            height=38,
            corner_radius=0,
            fg_color=self.c("green"),
            text_color="white",
            font=("Segoe UI Semibold", 13),
            padx=18,
        )
        self.status_bar.grid(row=1, column=0, sticky="ew")

    def _clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def _toggle_theme(self) -> None:
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        ctk.set_appearance_mode(self.theme_mode)
        self.root.configure(fg_color=self.c("window_bg"))
        self.content.configure(fg_color=self.c("window_bg"))
        self.status_bar.configure(fg_color=self.c("green"))
        if self.template_gallery_window and self.template_gallery_window.winfo_exists():
            self.template_gallery_window.destroy()
            self.template_gallery_window = None

        if self.current_screen == "actions":
            self._show_actions_screen()
        else:
            self._show_import_screen()

        self._set_status(f"{self.theme_mode.capitalize()} mode enabled.", self.c("green"))

    def _topbar(self, parent, show_back: bool = False) -> ctk.CTkFrame:
        bar = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        bar.grid_columnconfigure(1, weight=1)
        col = 0
        if show_back:
            self._button(
                bar,
                text="Back",
                command=self._show_import_screen,
                fg=self.c("button_soft"),
                hover=self.c("button_soft_hover"),
                text_color=self.c("text"),
                width=88,
                height=38,
                radius=18,
                font=("Segoe UI Semibold", 13),
            ).grid(row=0, column=0, padx=(0, 14))
            col = 1

        filler = ctk.CTkFrame(bar, fg_color="transparent", corner_radius=0)
        filler.grid(row=0, column=col, sticky="ew")
        filler.grid_columnconfigure(0, weight=1)

        self._button(
            bar,
            text="Dark Mode" if self.theme_mode == "light" else "Light Mode",
            command=self._toggle_theme,
            fg=self.c("button_soft"),
            hover=self.c("button_soft_hover"),
            text_color=self.c("text"),
            width=112,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=col + 1, sticky="e")
        return bar

    def _show_import_screen(self) -> None:
        self.current_screen = "import"
        self._clear_content()

        wrap = ctk.CTkFrame(self.content, fg_color=self.c("window_bg"), corner_radius=0)
        wrap.grid(row=0, column=0, sticky="nsew", padx=20, pady=12)
        wrap.grid_columnconfigure(0, weight=1)

        self._topbar(wrap).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        card = ctk.CTkFrame(
            wrap,
            fg_color=self.c("card_bg"),
            corner_radius=28,
            border_width=1,
            border_color=self.c("neutral"),
        )
        card.grid(row=1, column=0, sticky="n", pady=(0, 0))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Select CSV",
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 30),
        ).grid(row=0, column=0, padx=48, pady=(42, 10))

        self.import_csv_label = ctk.CTkLabel(
            card,
            text=Path(self.csv_path.get()).name if self.csv_path.get().strip() else "No CSV selected",
            text_color=self.c("muted"),
            font=("Segoe UI", 14),
        )
        self.import_csv_label.grid(row=1, column=0, padx=48, pady=(0, 24))

        actions = ctk.CTkFrame(card, fg_color="transparent", corner_radius=0)
        actions.grid(row=2, column=0, pady=(0, 18), padx=42)
        actions.grid_columnconfigure((0, 1), weight=1)

        self._button(
            actions,
            text="Choose CSV",
            command=self._choose_csv_and_continue,
            fg=self.c("green"),
            hover=self.c("green_hover"),
            text_color="white",
            width=170,
            height=46,
            radius=22,
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=0, padx=(0, 8))

        self._button(
            actions,
            text="Make Program",
            command=self._open_program_maker,
            fg=self.c("blue"),
            hover=self.c("blue_hover"),
            text_color="white",
            width=170,
            height=46,
            radius=22,
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=1, padx=(8, 0))

        if self.csv_path.get().strip():
            self._button(
                card,
                text="Use Current CSV",
                command=self._show_actions_screen,
                fg=self.c("button_soft"),
                hover=self.c("button_soft_hover"),
                text_color=self.c("text"),
                width=180,
                height=42,
                radius=20,
                font=("Segoe UI Semibold", 14),
            ).grid(row=3, column=0, pady=(0, 42))

    def _show_actions_screen(self) -> None:
        self.current_screen = "actions"
        self._clear_content()

        wrap = ctk.CTkFrame(self.content, fg_color=self.c("window_bg"), corner_radius=0)
        wrap.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=0)
        wrap.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(wrap, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        self._button(
            header,
            text="Back",
            command=self._show_import_screen,
            fg=self.c("button_soft"),
            hover=self.c("button_soft_hover"),
            text_color=self.c("text"),
            width=88,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=0, padx=(0, 14))

        ctk.CTkLabel(
            header,
            text="Choose an action",
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 25),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            header,
            text=Path(self.csv_path.get()).name,
            text_color=self.c("muted"),
            font=("Segoe UI", 13),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        self._button(
            header,
            text="Dark Mode" if self.theme_mode == "light" else "Light Mode",
            command=self._toggle_theme,
            fg=self.c("button_soft"),
            hover=self.c("button_soft_hover"),
            text_color=self.c("text"),
            width=112,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=2, rowspan=2, sticky="e")

        body = ctk.CTkFrame(wrap, fg_color="transparent", corner_radius=0)
        body.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        bulletin = self._panel(
            body,
            title="Bulletin Maker",
            subtitle="Use the sample PDF style for the program page.",
            accent=self.c("green"),
            soft=self.c("green_soft"),
            border=self.c("green_border"),
        )
        bulletin.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        slides = self._panel(
            body,
            title="Slides Generator",
            subtitle="Choose a template from a visual gallery and generate PowerPoint slides.",
            accent=self.c("amber"),
            soft=self.c("amber_soft"),
            border=self.c("amber_border"),
        )
        slides.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        lower_thirds = self._panel(
            body,
            title="Lower Thirds",
            subtitle="Generate 1920x1080 lower thirds based on the Canva-inspired blue banner design.",
            accent=self.c("blue"),
            soft=self.c("blue_soft"),
            border=self.c("blue_border"),
        )
        lower_thirds.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        self._build_bulletin_panel(bulletin)
        self._build_slides_panel(slides)
        self._build_lower_thirds_panel(lower_thirds)

    def _build_bulletin_panel(self, parent: ctk.CTkFrame) -> None:
        self._field(parent, row=2, label="PDF output", variable=self.pdf_output_path, button_text="Save As", button_command=self._choose_pdf_output, tone="green")

        ctk.CTkLabel(
            parent,
            text="Uses the fixed program layout with Filipino Service, Sabbath School, and Hour Of Worship from the CSV section rows.",
            text_color=self.c("muted"),
            font=("Segoe UI", 12),
            justify="left",
            wraplength=360,
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(4, 14))

        self._button(
            parent,
            text="Generate Bulletin",
            command=self._generate_pdf,
            fg=self.c("green"),
            hover=self.c("green_hover"),
            text_color="white",
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(0, 20))

    def _build_slides_panel(self, parent: ctk.CTkFrame) -> None:
        self._field(parent, row=2, label="Selected template", variable=self.template_path, button_text="Gallery", button_command=self._open_template_gallery, tone="amber")
        self._field(parent, row=5, label="Slides output", variable=self.slides_output_path, button_text="Save As", button_command=self._choose_slides_output, tone="amber")

        preview_bg = self.c("amber_soft") if self.theme_mode == "light" else "#2C241E"
        self.template_preview = ctk.CTkLabel(
            parent,
            text="No template selected",
            text_color=self.c("muted"),
            font=("Segoe UI", 12),
            anchor="center",
            justify="center",
            fg_color=preview_bg,
            corner_radius=18,
            height=170,
        )
        self.template_preview.grid(row=8, column=0, sticky="ew", padx=20, pady=(6, 14))

        self._button(
            parent,
            text="Generate Slides",
            command=self._generate_slides,
            fg=self.c("amber"),
            hover=self.c("amber_hover"),
            text_color="white",
        ).grid(row=9, column=0, sticky="w", padx=20, pady=(0, 20))

        self._refresh_template_preview()

    def _build_lower_thirds_panel(self, parent: ctk.CTkFrame) -> None:
        self._field(
            parent,
            row=2,
            label="Output folder",
            variable=self.lower_thirds_output_dir,
            button_text="Browse",
            button_command=self._choose_lower_thirds_output_dir,
            tone="blue",
        )

        ctk.CTkLabel(
            parent,
            text="Exports Canva-inspired transparent PNG lower thirds at 1920x1080 using the current CSV.",
            text_color=self.c("muted"),
            font=("Segoe UI", 12),
            justify="left",
            wraplength=760,
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(4, 14))

        self._button(
            parent,
            text="Generate Lower Thirds",
            command=self._generate_lower_thirds,
            fg=self.c("blue"),
            hover=self.c("blue_hover"),
            text_color="white",
            width=180,
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(0, 20))

    def _field(
        self,
        parent: ctk.CTkFrame,
        row: int,
        label: str,
        variable: tk.StringVar,
        button_text: str | None = None,
        button_command=None,
        tone: str = "green",
    ) -> None:
        if tone == "green":
            border = self.c("green_border")
            entry_bg = self.c("green_soft")
        elif tone == "amber":
            border = self.c("amber_border")
            entry_bg = self.c("amber_soft")
        else:
            border = self.c("blue_border")
            entry_bg = self.c("blue_soft")

        ctk.CTkLabel(
            parent,
            text=label,
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=20, pady=(0, 7))

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            fg_color=entry_bg,
            border_color=border,
            text_color=self.c("text"),
            height=42,
            corner_radius=18,
            font=("Segoe UI", 13),
        )
        entry.grid(row=row + 1, column=0, sticky="ew", padx=20)

        if button_text and button_command:
            action_row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
            action_row.grid(row=row + 2, column=0, sticky="ew", padx=20, pady=(8, 14))
            action_row.grid_columnconfigure(0, weight=1)
            self._button(
                action_row,
                text=button_text,
                command=button_command,
                fg=self.c("button_soft"),
                hover=self.c("button_soft_hover"),
                text_color=self.c("text"),
                width=92,
                height=36,
                radius=16,
                font=("Segoe UI Semibold", 13),
            ).grid(row=0, column=1, sticky="e")
        else:
            ctk.CTkFrame(parent, fg_color="transparent", height=14).grid(row=row + 2, column=0)

    def _open_template_gallery(self) -> None:
        if self.template_gallery_window and self.template_gallery_window.winfo_exists():
            self.template_gallery_window.focus()
            return

        window = ctk.CTkToplevel(self.root, fg_color=self.c("window_bg"))
        window.title("Template Gallery")
        window.geometry("920x640")
        window.transient(self.root)
        window.grab_set()
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)
        self.template_gallery_window = window

        header = ctk.CTkFrame(window, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Choose a Slide Template",
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 24),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Templates live in the local templates folder. Use the import tile to add more.",
            text_color=self.c("muted"),
            font=("Segoe UI", 13),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.gallery_frame = ctk.CTkScrollableFrame(window, fg_color=self.c("card_bg"), corner_radius=22)
        self.gallery_frame.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 22))
        self.gallery_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._populate_template_gallery()

    def _populate_template_gallery(self) -> None:
        for child in self.gallery_frame.winfo_children():
            child.destroy()

        add_tile = ctk.CTkFrame(
            self.gallery_frame,
            fg_color=self.c("amber_soft"),
            border_color=self.c("amber_border"),
            border_width=1,
            corner_radius=22,
        )
        add_tile.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        add_tile.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(add_tile, text="+", font=("Segoe UI Semibold", 44), text_color=self.c("amber")).grid(row=0, column=0, pady=(26, 10))
        ctk.CTkLabel(add_tile, text="Import Template", text_color=self.c("text"), font=("Segoe UI Semibold", 16)).grid(row=1, column=0)
        ctk.CTkLabel(add_tile, text="Copy a PPTX into the templates folder", text_color=self.c("muted"), font=("Segoe UI", 12)).grid(row=2, column=0, pady=(6, 18))
        self._button(
            add_tile,
            "Add Template",
            self._import_template_into_gallery,
            fg=self.c("amber"),
            hover=self.c("amber_hover"),
            text_color="white",
            width=150,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=3, column=0, pady=(0, 20))

        templates = list_templates()
        for index, template in enumerate(templates, start=1):
            row = index // 3
            column = index % 3
            self._template_tile(template).grid(row=row, column=column, padx=10, pady=10, sticky="nsew")

    def _template_tile(self, template: Path) -> ctk.CTkFrame:
        tile = ctk.CTkFrame(
            self.gallery_frame,
            fg_color=self.c("card_bg"),
            border_color=self.c("neutral"),
            border_width=1,
            corner_radius=22,
        )
        tile.grid_columnconfigure(0, weight=1)

        thumbnail_path = ensure_thumbnail(template)
        image = self._load_template_image(thumbnail_path)

        image_label = ctk.CTkLabel(tile, text="", image=image)
        image_label.image = image
        image_label.grid(row=0, column=0, padx=14, pady=(14, 10))

        ctk.CTkLabel(
            tile,
            text=template.stem.replace("_", " "),
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 15),
            wraplength=220,
            justify="center",
        ).grid(row=1, column=0, padx=14)

        ctk.CTkLabel(
            tile,
            text=template.name,
            text_color=self.c("muted"),
            font=("Segoe UI", 11),
            wraplength=220,
            justify="center",
        ).grid(row=2, column=0, padx=14, pady=(6, 12))

        self._button(
            tile,
            text="Use Template",
            command=lambda path=template: self._select_template(path),
            fg=self.c("amber"),
            hover=self.c("amber_hover"),
            text_color="white",
            width=150,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=3, column=0, pady=(0, 14))
        return tile

    def _import_template_into_gallery(self) -> None:
        path = filedialog.askopenfilename(
            title="Import PowerPoint template",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")],
        )
        if not path:
            return

        added = import_template(path)
        self._set_status(f"Template imported: {added.name}", self.c("status_success"))
        self._populate_template_gallery()

    def _select_template(self, template: Path) -> None:
        self.template_path.set(str(template))
        self._refresh_template_preview()
        self._set_status(f"Template selected: {template.name}", self.c("status_success"))
        if self.template_gallery_window and self.template_gallery_window.winfo_exists():
            self.template_gallery_window.destroy()
            self.template_gallery_window = None

    def _refresh_template_preview(self) -> None:
        template = self.template_path.get().strip()
        if not template:
            self.template_preview.configure(text="No template selected", image=None)
            self.template_preview_image = None
            return

        thumbnail = ensure_thumbnail(template)
        image = self._load_template_image(thumbnail, size=(320, 180))
        self.template_preview_image = image
        self.template_preview.configure(text="", image=image)

    def _load_template_image(self, thumbnail_path: Path | None, size: tuple[int, int] = (240, 135)) -> ctk.CTkImage:
        if thumbnail_path and thumbnail_path.exists():
            image = Image.open(thumbnail_path)
        else:
            image = self._placeholder_template_image(*size)
        return ctk.CTkImage(light_image=image, dark_image=image, size=size)

    def _make_gradient_image(self, width: int, height: int) -> ctk.CTkImage:
        image = Image.new("RGB", (width, height), self.c("window_bg"))
        draw = ImageDraw.Draw(image)
        if self.theme_mode == "light":
            top = (226, 238, 232)
            bottom = (247, 232, 219)
            outline = "#EEE2D6"
            fill = "#FFFDFB"
            top_band = "#D8E7E1"
            left_panel = "#F5EFE8"
            right_panel = "#F8F1E8"
        else:
            top = (39, 55, 50)
            bottom = (53, 38, 29)
            outline = "#3F3832"
            fill = "#26211E"
            top_band = "#2D413B"
            left_panel = "#2A2623"
            right_panel = "#302720"

        for y in range(height):
            mix = y / max(1, height - 1)
            color = tuple(int(top[i] + ((bottom[i] - top[i]) * mix)) for i in range(3))
            draw.line((0, y, width, y), fill=color)

        draw.rounded_rectangle((38, 50, width - 38, height - 50), radius=34, outline=outline, width=3, fill=fill)
        draw.rounded_rectangle((72, 82, width - 72, 136), radius=16, fill=top_band)
        draw.rounded_rectangle((82, 166, (width // 2) - 12, height - 86), radius=18, fill=left_panel)
        draw.rounded_rectangle(((width // 2) + 12, 166, width - 82, height - 86), radius=18, fill=right_panel)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))

    def _placeholder_template_image(self, width: int, height: int) -> Image.Image:
        if self.theme_mode == "light":
            bg = "#FBF4EC"
            outline = "#DEC5AE"
            fill = "#FFF8F1"
            band = "#E9D7C6"
            panel = "#F5EBDD"
        else:
            bg = "#2B241E"
            outline = "#755438"
            fill = "#241F1B"
            band = "#4B382A"
            panel = "#302720"

        image = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, width - 8, height - 8), radius=20, outline=outline, width=2, fill=fill)
        draw.rounded_rectangle((24, 22, width - 24, 52), radius=12, fill=band)
        draw.rectangle((30, 70, width - 30, height - 24), fill=panel)
        return image

    def _choose_csv_and_continue(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        self.csv_path.set(path)
        self.import_csv_label.configure(text=Path(path).name)
        self._prefill_outputs(path)
        self._show_actions_screen()
        self._set_status("CSV selected.", self.c("status_success"))

    def _open_program_maker(self) -> None:
        if self.program_maker_window and self.program_maker_window.window.winfo_exists():
            self.program_maker_window.window.focus()
            return

        self.program_maker_window = ProgramMakerWindow(self)

    def _choose_pdf_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save bulletin PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf_output_path.set(path)

    def _choose_slides_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save slides as",
            defaultextension=".pptx",
            filetypes=[("PowerPoint files", "*.pptx")],
        )
        if path:
            self.slides_output_path.set(path)

    def _choose_lower_thirds_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose lower thirds output folder")
        if path:
            self.lower_thirds_output_dir.set(path)

    def _prefill_outputs(self, csv_path: str) -> None:
        csv_file = Path(csv_path)
        output_dir = csv_file.parent / "output"
        stem = csv_file.stem
        self.pdf_output_path.set(str(output_dir / f"{stem}_program.pdf"))
        self.slides_output_path.set(str(output_dir / f"{stem}_slides.pptx"))
        self.lower_thirds_output_dir.set(str(output_dir / "lower_thirds"))

    def _generate_pdf(self) -> None:
        csv_path = self.csv_path.get().strip()
        output_path = self.pdf_output_path.get().strip()

        if not csv_path:
            messagebox.showerror("Missing CSV", "Choose a CSV file first.")
            return
        if not output_path:
            messagebox.showerror("Missing Output", "Choose where to save the bulletin PDF.")
            return

        try:
            from .bulletin_pdf import build_bulletin_pdf

            build_bulletin_pdf(csv_path, output_path)
            self._set_status(f"Bulletin PDF created: {output_path}", self.c("status_success"))
            messagebox.showinfo("Success", f"Bulletin PDF created:\n{output_path}")
        except Exception as exc:
            self._set_status(f"PDF generation failed: {exc}", self.c("status_error"))
            messagebox.showerror("PDF Generation Failed", str(exc))

    def _generate_slides(self) -> None:
        csv_path = self.csv_path.get().strip()
        template_path = self.template_path.get().strip()
        output_path = self.slides_output_path.get().strip()

        if not csv_path:
            messagebox.showerror("Missing CSV", "Choose a CSV file first.")
            return
        if not template_path:
            messagebox.showerror("Missing Template", "Choose a PowerPoint template first.")
            return
        if not output_path:
            messagebox.showerror("Missing Output", "Choose where to save the PowerPoint file.")
            return

        try:
            generate_slides(template_path, csv_path, output_path)
            self._set_status(f"PowerPoint created: {output_path}", self.c("status_success"))
            messagebox.showinfo("Success", f"PowerPoint created:\n{output_path}")
        except RuntimeError as exc:
            self._set_status(str(exc), self.c("status_error"))
            messagebox.showerror("Slides Generation Failed", str(exc))
        except Exception as exc:
            self._set_status(f"Slides generation failed: {exc}", self.c("status_error"))
            messagebox.showerror("Slides Generation Failed", str(exc))

    def _generate_lower_thirds(self) -> None:
        csv_path = self.csv_path.get().strip()
        output_dir = self.lower_thirds_output_dir.get().strip()

        if not csv_path:
            messagebox.showerror("Missing CSV", "Choose a CSV file first.")
            return
        if not output_dir:
            messagebox.showerror("Missing Output", "Choose a folder for the lower thirds.")
            return

        try:
            exported = export_lower_thirds(csv_path, output_dir)
            self._set_status(f"Lower thirds created: {len(exported)} file(s)", self.c("status_success"))
            messagebox.showinfo("Success", f"Lower thirds created:\n{len(exported)} file(s)\n{output_dir}")
        except Exception as exc:
            self._set_status(f"Lower thirds generation failed: {exc}", self.c("status_error"))
            messagebox.showerror("Lower Thirds Failed", str(exc))

    def _panel(self, parent, title: str, subtitle: str, accent: str, soft: str, border: str) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, fg_color=self.c("card_bg"), corner_radius=26, border_width=1, border_color=border)
        panel.grid_columnconfigure(0, weight=1)

        accent_bar = ctk.CTkFrame(panel, fg_color=soft, corner_radius=18, height=56)
        accent_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 16))
        accent_bar.grid_columnconfigure(0, weight=1)
        accent_bar.grid_rowconfigure(0, weight=1)
        accent_bar.grid_propagate(False)

        ctk.CTkLabel(
            accent_bar,
            text=title,
            text_color=accent,
            font=("Segoe UI Semibold", 22),
            anchor="center",
            justify="center",
        ).grid(row=0, column=0, sticky="nsew", padx=18, pady=0)

        ctk.CTkLabel(
            panel,
            text=subtitle,
            text_color=self.c("muted"),
            font=("Segoe UI", 13),
            justify="left",
            wraplength=360,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        return panel

    def _button(
        self,
        parent,
        text: str,
        command,
        fg: str,
        hover: str,
        text_color: str,
        width: int = 140,
        height: int = 42,
        radius: int = 20,
        font: tuple[str, int] | tuple[str, int, str] = ("Segoe UI Semibold", 14),
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            width=width,
            height=height,
            corner_radius=radius,
            font=font,
        )

    def _set_status(self, text: str, color: str) -> None:
        self.status_text.set(text)
        self.status_bar.configure(fg_color=color)


class ProgramMakerWindow:
    SECTIONS = [
        ("Filipino Service", "9:00 am"),
        ("Sabbath School", "10:00 am"),
        ("Hour Of Worship", "11:15 am"),
    ]

    def __init__(self, app: BulletinApp) -> None:
        self.app = app
        self.window = ctk.CTkToplevel(app.root, fg_color=app.c("window_bg"))
        self.window.title("Program Maker")
        self.window.geometry("1120x760")
        self.window.minsize(980, 680)
        self.window.transient(app.root)
        self.window.grab_set()
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.saved_path = tk.StringVar()
        self.rows_by_section: dict[str, list[dict[str, object]]] = {
            title: [] for title, _ in self.SECTIONS
        }

        self._build()
        self._load_template_rows()

    def _build(self) -> None:
        header = ctk.CTkFrame(self.window, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header.grid_columnconfigure(1, weight=1)

        self.app._button(
            header,
            text="Close",
            command=self.close,
            fg=self.app.c("button_soft"),
            hover=self.app.c("button_soft_hover"),
            text_color=self.app.c("text"),
            width=92,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=0, rowspan=2, padx=(0, 14), sticky="w")

        ctk.CTkLabel(
            header,
            text="Program Maker",
            text_color=self.app.c("text"),
            font=("Segoe UI Semibold", 28),
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            header,
            text="Build a clean program CSV with the correct columns and fixed service sections.",
            text_color=self.app.c("muted"),
            font=("Segoe UI", 13),
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        status_frame = ctk.CTkFrame(
            header,
            fg_color=self.app.c("card_bg"),
            corner_radius=18,
            border_width=1,
            border_color=self.app.c("neutral"),
        )
        status_frame.grid(row=0, column=2, rowspan=2, sticky="e")
        ctk.CTkLabel(
            status_frame,
            text="Save target",
            text_color=self.app.c("muted"),
            font=("Segoe UI Semibold", 12),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(
            status_frame,
            textvariable=self.saved_path,
            text_color=self.app.c("text"),
            font=("Segoe UI", 12),
            wraplength=260,
            justify="right",
        ).grid(row=1, column=0, sticky="e", padx=16, pady=(0, 12))

        shell = ctk.CTkFrame(
            self.window,
            fg_color=self.app.c("card_bg"),
            corner_radius=28,
            border_width=1,
            border_color=self.app.c("neutral"),
        )
        shell.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(shell, fg_color="transparent", corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 6))
        toolbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            toolbar,
            text="Template",
            text_color=self.app.c("text"),
            font=("Segoe UI Semibold", 16),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            toolbar,
            text="The CSV will save as title / subheading / small_subheading and include all three section breaks.",
            text_color=self.app.c("muted"),
            font=("Segoe UI", 12),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.app._button(
            toolbar,
            text="Reset Template",
            command=self._reset_template,
            fg=self.app.c("button_soft"),
            hover=self.app.c("button_soft_hover"),
            text_color=self.app.c("text"),
            width=120,
            height=36,
            radius=16,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=2, rowspan=2, sticky="e")

        self.editor = ctk.CTkScrollableFrame(shell, fg_color="transparent", corner_radius=0)
        self.editor.grid(row=1, column=0, sticky="nsew", padx=18, pady=(6, 10))
        self.editor.grid_columnconfigure(0, weight=1)

        self.section_frames: dict[str, ctk.CTkFrame] = {}
        self.section_rows_frames: dict[str, ctk.CTkFrame] = {}
        for index, (section_title, section_time) in enumerate(self.SECTIONS):
            panel = self._build_section_panel(section_title, section_time)
            panel.grid(row=index, column=0, sticky="ew", pady=(0, 16))

        footer = ctk.CTkFrame(shell, fg_color="transparent", corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=22, pady=(4, 20))
        footer.grid_columnconfigure(0, weight=1)

        self.app._button(
            footer,
            text="Save",
            command=self._save_only,
            fg=self.app.c("button_soft"),
            hover=self.app.c("button_soft_hover"),
            text_color=self.app.c("text"),
            width=110,
            height=42,
            radius=20,
            font=("Segoe UI Semibold", 14),
        ).grid(row=0, column=1, padx=(0, 10))

        self.app._button(
            footer,
            text="Save + Use",
            command=self._save_and_use,
            fg=self.app.c("blue"),
            hover=self.app.c("blue_hover"),
            text_color="white",
            width=128,
            height=42,
            radius=20,
            font=("Segoe UI Semibold", 14),
        ).grid(row=0, column=2)

    def _build_section_panel(self, section_title: str, section_time: str) -> ctk.CTkFrame:
        accent = self.app.c("blue") if section_title == "Hour Of Worship" else self.app.c("green")
        soft = self.app.c("blue_soft") if section_title == "Hour Of Worship" else self.app.c("green_soft")
        border = self.app.c("blue_border") if section_title == "Hour Of Worship" else self.app.c("green_border")

        panel = ctk.CTkFrame(
            self.editor,
            fg_color=self.app.c("card_bg"),
            corner_radius=24,
            border_width=1,
            border_color=border,
        )
        panel.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=0)
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)

        title_bar = ctk.CTkFrame(top, fg_color=soft, corner_radius=18, height=48)
        title_bar.grid(row=0, column=0, sticky="ew")
        title_bar.grid_columnconfigure(0, weight=1)
        title_bar.grid_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text=section_title,
            text_color=accent,
            font=("Segoe UI Semibold", 20),
        ).grid(row=0, column=0, sticky="w", padx=(20, 0))

        ctk.CTkLabel(
            title_bar,
            text=section_time,
            text_color=accent,
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=0, sticky="e", padx=(0, 20))

        labels = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=0)
        labels.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 4))
        labels.grid_columnconfigure(0, weight=4)
        labels.grid_columnconfigure(1, weight=3)
        labels.grid_columnconfigure(2, weight=3)

        ctk.CTkLabel(
            labels,
            text="Title",
            text_color=self.app.c("muted"),
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(6, 8))

        ctk.CTkLabel(
            labels,
            text="Name / Subheading",
            text_color=self.app.c("muted"),
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=8)

        ctk.CTkLabel(
            labels,
            text="Extra / Small Subheading",
            text_color=self.app.c("muted"),
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=(8, 52))

        rows_frame = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=0)
        rows_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 8))
        rows_frame.grid_columnconfigure(0, weight=4)
        rows_frame.grid_columnconfigure(1, weight=3)
        rows_frame.grid_columnconfigure(2, weight=3)

        actions = ctk.CTkFrame(panel, fg_color="transparent", corner_radius=0)
        actions.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        actions.grid_columnconfigure(0, weight=1)

        self.app._button(
            actions,
            text="Add Row",
            command=lambda title=section_title: self._add_row(title),
            fg=accent,
            hover=self.app.c("blue_hover") if section_title == "Hour Of Worship" else self.app.c("green_hover"),
            text_color="white",
            width=110,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=1, sticky="e")

        self.section_frames[section_title] = panel
        self.section_rows_frames[section_title] = rows_frame
        return panel

    def _load_template_rows(self) -> None:
        starter_counts = {
            "Filipino Service": 3,
            "Sabbath School": 3,
            "Hour Of Worship": 5,
        }
        for section_title, _ in self.SECTIONS:
            for _ in range(starter_counts[section_title]):
                self._add_row(section_title)

    def _reset_template(self) -> None:
        for section_title in list(self.rows_by_section):
            for row_data in self.rows_by_section[section_title]:
                frame = row_data["frame"]
                if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
                    frame.destroy()
            self.rows_by_section[section_title] = []
        self._load_template_rows()

    def _entry(self, parent, variable: tk.StringVar, placeholder: str, tone: str) -> ctk.CTkEntry:
        border = self.app.c("blue_border") if tone == "blue" else self.app.c("green_border")
        soft = self.app.c("blue_soft") if tone == "blue" else self.app.c("green_soft")
        return ctk.CTkEntry(
            parent,
            textvariable=variable,
            placeholder_text=placeholder,
            fg_color=soft,
            border_color=border,
            text_color=self.app.c("text"),
            height=40,
            corner_radius=16,
            font=("Segoe UI", 13),
        )

    def _add_row(
        self,
        section_title: str,
        title: str = "",
        subheading: str = "",
        small_subheading: str = "",
    ) -> None:
        rows_frame = self.section_rows_frames[section_title]
        tone = "blue" if section_title == "Hour Of Worship" else "green"

        title_var = tk.StringVar(value=title)
        subheading_var = tk.StringVar(value=subheading)
        small_subheading_var = tk.StringVar(value=small_subheading)

        row_frame = ctk.CTkFrame(rows_frame, fg_color="transparent", corner_radius=0)
        row_frame.grid_columnconfigure(0, weight=4)
        row_frame.grid_columnconfigure(1, weight=3)
        row_frame.grid_columnconfigure(2, weight=3)
        row_frame.grid(row=len(self.rows_by_section[section_title]), column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self._entry(row_frame, title_var, "Program item title", tone).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry(row_frame, subheading_var, "Name or subheading", tone).grid(row=0, column=1, sticky="ew", padx=8)
        self._entry(row_frame, small_subheading_var, "Extra line", tone).grid(row=0, column=2, sticky="ew", padx=(8, 48))

        row_data = {
            "frame": row_frame,
            "title": title_var,
            "subheading": subheading_var,
            "small_subheading": small_subheading_var,
        }

        self.app._button(
            row_frame,
            text="Remove",
            command=lambda data=row_data, section=section_title: self._remove_row(section, data),
            fg=self.app.c("button_soft"),
            hover=self.app.c("button_soft_hover"),
            text_color=self.app.c("text"),
            width=84,
            height=34,
            radius=16,
            font=("Segoe UI Semibold", 12),
        ).grid(row=0, column=3, sticky="e")

        self.rows_by_section[section_title].append(row_data)

    def _remove_row(self, section_title: str, row_data: dict[str, object]) -> None:
        frame = row_data["frame"]
        if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
            frame.destroy()
        self.rows_by_section[section_title] = [row for row in self.rows_by_section[section_title] if row is not row_data]
        self._reflow_rows(section_title)

    def _reflow_rows(self, section_title: str) -> None:
        for index, row_data in enumerate(self.rows_by_section[section_title]):
            frame = row_data["frame"]
            if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
                frame.grid_configure(row=index)

    def _serialize_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for section_title, section_time in self.SECTIONS:
            rows.append(
                {
                    "title": section_title,
                    "subheading": section_time,
                    "small_subheading": "",
                }
            )
            for row_data in self.rows_by_section[section_title]:
                title = str(row_data["title"].get()).strip()
                subheading = str(row_data["subheading"].get()).strip()
                small_subheading = str(row_data["small_subheading"].get()).strip()
                if not any((title, subheading, small_subheading)):
                    continue
                rows.append(
                    {
                        "title": title,
                        "subheading": subheading,
                        "small_subheading": small_subheading,
                    }
                )
        return rows

    def _write_csv(self, path: str) -> None:
        rows = self._serialize_rows()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["title", "subheading", "small_subheading"])
            writer.writeheader()
            writer.writerows(rows)
        self.saved_path.set(str(target))

    def _prompt_save_path(self) -> str | None:
        suggested = Path(self.saved_path.get()) if self.saved_path.get().strip() else Path.cwd() / "program.csv"
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save program CSV as",
            defaultextension=".csv",
            initialfile=suggested.name,
            initialdir=str(suggested.parent),
            filetypes=[("CSV files", "*.csv")],
        )
        return path or None

    def _save_only(self) -> None:
        path = self._prompt_save_path()
        if not path:
            return
        self._write_csv(path)
        self.app._set_status(f"Program CSV saved: {path}", self.app.c("status_success"))
        messagebox.showinfo("Saved", f"Program CSV saved:\n{path}", parent=self.window)

    def _save_and_use(self) -> None:
        path = self._prompt_save_path()
        if not path:
            return
        self._write_csv(path)
        self.app.csv_path.set(path)
        self.app._prefill_outputs(path)
        if hasattr(self.app, "import_csv_label") and self.app.import_csv_label.winfo_exists():
            self.app.import_csv_label.configure(text=Path(path).name)
        self.app._show_actions_screen()
        self.app._set_status(f"Program CSV ready: {path}", self.app.c("status_success"))
        self.close()

    def close(self) -> None:
        if self.window.winfo_exists():
            self.window.grab_release()
            self.window.destroy()
        self.app.program_maker_window = None


def launch_gui() -> None:
    BulletinApp().run()
