from __future__ import annotations

import csv
import ctypes
import os
import subprocess
import customtkinter as ctk
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

from .data import load_bulletin_sections
from .lower_thirds import export_lower_thirds
from .paths import assets_dir
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
        self._set_windows_app_id()

        self.root = ctk.CTk(fg_color=self.c("window_bg"))
        self.root.title("GFAC Bulletin Studio")
        self.root.geometry("980x940")
        self.root.minsize(920, 820)
        self.root.attributes("-alpha", 0.0)
        self.window_icon_image = None
        self._apply_window_icon(self.root)

        self.csv_path = tk.StringVar()
        self.pdf_output_path = tk.StringVar()
        self.template_path = tk.StringVar()
        self.slides_output_path = tk.StringVar()
        self.lower_thirds_output_dir = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose a CSV file to begin.")

        self.template_preview_image: ctk.CTkImage | None = None
        self.hero_image: ctk.CTkImage | None = None
        self.brand_lockup_image: ctk.CTkImage | None = None
        self.welcome_background_photo = None
        self.actions_background_photo = None
        self.welcome_brand_photo = None
        self.welcome_create_photo = None
        self.welcome_import_photo = None
        self.welcome_redraw_job = None
        self.actions_redraw_job = None
        self.intro_logo_image: ctk.CTkImage | None = None
        self.intro_title_image: ctk.CTkImage | None = None
        self.intro_splash: ctk.CTkToplevel | None = None
        self.theme_transition = False
        self.template_gallery_window: ctk.CTkToplevel | None = None
        self.program_maker_window: ProgramMakerWindow | None = None
        self.current_screen = "import"

        self._build_shell()
        self._show_import_screen()
        self.root.after(120, self._start_intro_animation)

    def c(self, key: str) -> str:
        return THEMES[self.theme_mode][key]

    def run(self) -> None:
        self.root.mainloop()

    def _set_windows_app_id(self) -> None:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GFAC.BulletinStudio")
        except Exception:
            pass

    def _apply_window_icon(self, window) -> None:
        ico_path = assets_dir() / "app.ico"
        png_path = assets_dir() / "gfac_logo_white.png"

        try:
            if ico_path.exists():
                window.iconbitmap(default=str(ico_path))
        except Exception:
            pass

        try:
            if png_path.exists():
                self.window_icon_image = tk.PhotoImage(file=str(png_path))
                window.iconphoto(True, self.window_icon_image)
        except Exception:
            pass

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
        if self.welcome_redraw_job:
            try:
                self.root.after_cancel(self.welcome_redraw_job)
            except Exception:
                pass
            self.welcome_redraw_job = None
        if self.actions_redraw_job:
            try:
                self.root.after_cancel(self.actions_redraw_job)
            except Exception:
                pass
            self.actions_redraw_job = None
        for child in self.content.winfo_children():
            child.destroy()

    def _toggle_theme(self) -> None:
        if self.intro_splash and self.intro_splash.winfo_exists():
            return
        if self.theme_transition:
            return

        target_mode = "dark" if self.theme_mode == "light" else "light"
        self._start_theme_transition(target_mode)

    def _apply_theme_mode(self, theme_mode: str) -> None:
        self.theme_mode = theme_mode
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

    def _start_theme_transition(self, target_mode: str) -> None:
        self.theme_transition = True
        self._advance_theme_transition(target_mode, phase=0, alpha=1.0)

    def _advance_theme_transition(self, target_mode: str, phase: int, alpha: float) -> None:
        if phase == 0:
            next_alpha = max(0.9, alpha - 0.03)
            self.root.attributes("-alpha", next_alpha)
            if next_alpha <= 0.9:
                self._apply_theme_mode(target_mode)
                self.root.after(16, lambda: self._advance_theme_transition(target_mode, 1, next_alpha))
            else:
                self.root.after(16, lambda: self._advance_theme_transition(target_mode, 0, next_alpha))
            return

        next_alpha = min(1.0, alpha + 0.03)
        self.root.attributes("-alpha", next_alpha)
        if next_alpha >= 1.0:
            self.root.attributes("-alpha", 1.0)
            self.theme_transition = False
        else:
            self.root.after(16, lambda: self._advance_theme_transition(target_mode, 1, next_alpha))

    def _start_intro_animation(self) -> None:
        if self.intro_splash and self.intro_splash.winfo_exists():
            return

        self.root.update_idletasks()
        self.intro_logo_image = self._build_intro_logo_image()
        self.intro_title_image = self._build_intro_title_image()

        splash = ctk.CTkToplevel(self.root, fg_color="#0D1320")
        self._apply_window_icon(splash)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)
        splash.attributes("-alpha", 0.0)
        splash.geometry(
            f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}"
        )
        splash.grid_columnconfigure(0, weight=1)
        splash.grid_rowconfigure(0, weight=1)
        self.intro_splash = splash

        center = ctk.CTkFrame(splash, fg_color="transparent", corner_radius=0)
        center.grid(row=0, column=0)
        center.grid_columnconfigure(0, weight=1)

        intro_label = ctk.CTkLabel(
            center,
            text="",
            image=self.intro_logo_image,
        )
        intro_label.grid(row=0, column=0, pady=(0, 6))
        intro_label.image = self.intro_logo_image

        title_label = ctk.CTkLabel(
            center,
            text="" if self.intro_title_image else "Bulletin Studio",
            image=self.intro_title_image,
            text_color="#F5F7FB",
            font=("Segoe UI Semibold", 22),
        )
        title_label.grid(row=1, column=0)
        title_label.image = self.intro_title_image

        self.root.after(40, lambda: self._advance_intro_alpha(0, 0.0))

    def _build_intro_logo_image(self) -> ctk.CTkImage | None:
        logo_path = assets_dir() / "gfac_logo_white.png"
        if not logo_path.exists():
            return None

        logo = Image.open(logo_path).convert("RGBA")
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)

        max_width = 220
        scale = max_width / max(1, logo.width)
        logo = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)

        padding = 34
        padded_logo = Image.new("RGBA", (logo.width + (padding * 2), logo.height + (padding * 2)), (0, 0, 0, 0))
        padded_logo.alpha_composite(logo, (padding, padding))

        alpha = padded_logo.getchannel("A")
        glow_mask = alpha.filter(ImageFilter.GaussianBlur(20))
        glow_color = Image.new("RGBA", padded_logo.size, (56, 120, 220, 0))
        glow_color.putalpha(glow_mask.point(lambda value: min(180, int(value * 0.7))))

        composite = Image.new("RGBA", padded_logo.size, (0, 0, 0, 0))
        composite.alpha_composite(glow_color)
        composite.alpha_composite(padded_logo)

        return ctk.CTkImage(light_image=composite, dark_image=composite, size=composite.size)

    def _build_intro_title_image(self) -> ctk.CTkImage | None:
        font_path = assets_dir() / "TAN-KINDRED-Regular.otf"
        if not font_path.exists():
            return None

        try:
            font = ImageFont.truetype(str(font_path), 34)
        except OSError:
            return None

        text = "Bulletin Studio"
        probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(probe)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])

        image = Image.new("RGBA", (width + 12, height + 12), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.text((6 - bbox[0], 6 - bbox[1]), text, font=font, fill="#F5F7FB")
        return ctk.CTkImage(light_image=image, dark_image=image, size=image.size)

    def _build_brand_lockup_image(self) -> Image.Image | None:
        logo_path = assets_dir() / "gfac_logo_white.png"
        font_path = assets_dir() / "TAN-KINDRED-Regular.otf"
        if not logo_path.exists():
            return None

        logo = Image.open(logo_path).convert("RGBA")
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        logo = logo.resize((220, int(logo.height * (220 / max(1, logo.width)))), Image.LANCZOS)

        title_font = None
        if font_path.exists():
            try:
                title_font = ImageFont.truetype(str(font_path), 28)
            except OSError:
                title_font = None

        subtitle_text = "Program Studio"
        probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(probe)
        if title_font:
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=title_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]
        else:
            subtitle_width = 180
            subtitle_height = 28

        canvas_width = max(logo.width, subtitle_width) + 20
        canvas_height = logo.height + subtitle_height + 24
        image = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

        logo_x = (canvas_width - logo.width) // 2
        image.alpha_composite(logo, (logo_x, 0))

        draw = ImageDraw.Draw(image)
        if title_font:
            subtitle_x = (canvas_width - subtitle_width) // 2
            subtitle_y = logo.height - 2
            for offset in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                draw.text((subtitle_x + offset[0], subtitle_y + offset[1]), subtitle_text, font=title_font, fill=(255, 255, 255, 70))
            draw.text((subtitle_x, subtitle_y), subtitle_text, font=title_font, fill="#F7F9FF")
        else:
            draw.text((10, logo.height), subtitle_text, fill="#F7F9FF")

        return image

    def _advance_intro_alpha(self, phase: int, alpha: float) -> None:
        if not self.intro_splash or not self.intro_splash.winfo_exists():
            return

        if phase == 0:
            next_alpha = min(1.0, alpha + 0.08)
            self.intro_splash.attributes("-alpha", next_alpha)
            if next_alpha >= 1.0:
                self.root.after(1300, lambda: self._advance_intro_alpha(1, 1.0))
            else:
                self.root.after(40, lambda: self._advance_intro_alpha(0, next_alpha))
            return

        if phase == 1:
            next_alpha = max(0.0, alpha - 0.06)
            self.intro_splash.attributes("-alpha", next_alpha)
            self.root.attributes("-alpha", min(1.0, 1.0 - next_alpha))
            if next_alpha <= 0.0:
                self._finish_intro_animation()
            else:
                self.root.after(45, lambda: self._advance_intro_alpha(1, next_alpha))

    def _finish_intro_animation(self) -> None:
        self.root.attributes("-alpha", 1.0)
        if self.intro_splash and self.intro_splash.winfo_exists():
            self.intro_splash.destroy()
        self.intro_splash = None

    def _topbar(self, parent, show_back: bool = False) -> ctk.CTkFrame:
        bar = ctk.CTkFrame(
            parent,
            fg_color=self.c("card_bg"),
            corner_radius=24,
            border_width=1,
            border_color=self.c("neutral"),
            height=66,
        )
        bar.grid_rowconfigure(0, weight=1)
        bar.grid_columnconfigure(2, weight=1)
        bar.grid_propagate(False)

        brand = ctk.CTkFrame(bar, fg_color="transparent", corner_radius=0)
        brand.grid(row=0, column=0, sticky="w", padx=(18, 10), pady=0)
        brand.grid_rowconfigure(0, weight=1)

        brand_mark = ctk.CTkFrame(brand, fg_color=self.c("blue"), width=28, height=28, corner_radius=14)
        brand_mark.grid(row=0, column=0, padx=(0, 10), sticky="ns")
        brand_mark.grid_propagate(False)

        ctk.CTkLabel(
            brand,
            text="GFAC Bulletin Studio",
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 15),
        ).grid(row=0, column=1, sticky="w")

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
            ).grid(row=0, column=1, padx=(0, 12), sticky="w")

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
        ).grid(row=0, column=3, sticky="e", padx=18)
        return bar

    def _show_import_screen(self) -> None:
        self.current_screen = "import"
        self._clear_content()

        wrap = ctk.CTkFrame(self.content, fg_color=self.c("window_bg"), corner_radius=0)
        wrap.grid(row=0, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        background = tk.Label(wrap, bd=0, highlightthickness=0)
        background.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.brand_lockup_image = self._build_brand_lockup_image()

        create_button = tk.Label(wrap, bd=0, highlightthickness=0, cursor="hand2")
        create_button.place(relx=0.5, rely=0.59, anchor="center")
        create_button.bind("<Button-1>", lambda _event: self._open_program_maker())

        import_button = tk.Label(wrap, bd=0, highlightthickness=0, cursor="hand2")
        import_button.place(relx=0.5, rely=0.66, anchor="center")
        import_button.bind("<Button-1>", lambda _event: self._choose_csv_and_continue())

        mode_holder = ctk.CTkFrame(wrap, fg_color="#8A70D9", corner_radius=0, border_width=0)
        mode_holder.place(relx=0.965, rely=0.05, anchor="ne")

        self._button(
            mode_holder,
            text="Dark Mode" if self.theme_mode == "light" else "Light Mode",
            command=self._toggle_theme,
            fg="#433C69" if self.theme_mode == "dark" else "#D9CFF4",
            hover="#564B85" if self.theme_mode == "dark" else "#C7B8EE",
            text_color="white" if self.theme_mode == "dark" else "#2D205C",
            width=112,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=0)

        def refresh_welcome_background():
            width = max(wrap.winfo_width(), self.root.winfo_width(), 980)
            height = max(wrap.winfo_height(), self.root.winfo_height() - 38, 650)
            image = self._make_gradient_pil(width, height, variant="welcome")
            if self.brand_lockup_image:
                brand = self.brand_lockup_image
                brand_x = (width - brand.width) // 2
                brand_y = max(80, int(height * 0.25))
                image = image.convert("RGBA")
                image.alpha_composite(brand, (brand_x, brand_y))
            create_image = self._build_welcome_button_image(
                image,
                center_x_ratio=0.5,
                center_y_ratio=0.59,
                text="Create Program",
                fill="#1AA8C3",
            )
            import_image = self._build_welcome_button_image(
                image,
                center_x_ratio=0.5,
                center_y_ratio=0.66,
                text="Import CSV",
                fill="#C542D2",
            )
            image = image.convert("RGB")
            self.welcome_background_photo = ImageTk.PhotoImage(image)
            self.welcome_create_photo = ImageTk.PhotoImage(create_image)
            self.welcome_import_photo = ImageTk.PhotoImage(import_image)
            create_button.configure(image=self.welcome_create_photo, bg="#000001")
            import_button.configure(image=self.welcome_import_photo, bg="#000001")
            background.configure(image=self.welcome_background_photo, bg="#000001")
            create_button.image = self.welcome_create_photo
            import_button.image = self.welcome_import_photo
            mode_holder.configure(fg_color=self._welcome_surface_color(0.94, 0.06))

        def schedule_welcome_background(event=None):
            if self.welcome_redraw_job:
                wrap.after_cancel(self.welcome_redraw_job)
            self.welcome_redraw_job = wrap.after(50, refresh_welcome_background)

        wrap.bind("<Configure>", schedule_welcome_background)
        refresh_welcome_background()

    def _show_actions_screen(self) -> None:
        self.current_screen = "actions"
        self._clear_content()

        wrap = ctk.CTkFrame(self.content, fg_color=self.c("window_bg"), corner_radius=0)
        wrap.grid(row=0, column=0, sticky="nsew", padx=22, pady=16)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        topbar = self._topbar(wrap, show_back=True)
        topbar.grid(row=0, column=0, sticky="ew")

        page = ctk.CTkScrollableFrame(
            wrap,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=self.c("button_soft"),
            scrollbar_button_hover_color=self.c("button_soft_hover"),
        )
        page.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        page.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(page, fg_color="transparent", corner_radius=0)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)

        hero_card = ctk.CTkFrame(
            hero,
            fg_color=self.c("card_bg"),
            corner_radius=30,
            border_width=1,
            border_color=self.c("neutral"),
        )
        hero_card.grid(row=0, column=0, pady=(0, 0))
        hero_card.grid_columnconfigure(0, weight=1)

        glow = ctk.CTkFrame(
            hero_card,
            fg_color=self.c("blue_soft"),
            corner_radius=24,
            border_width=1,
            border_color=self.c("blue_border"),
            height=96,
            width=520,
        )
        glow.grid(row=0, column=0, padx=20, pady=20)
        glow.grid_propagate(False)
        glow.grid_columnconfigure(0, weight=1)
        glow.grid_columnconfigure(1, weight=0)
        glow.grid_rowconfigure(0, weight=1)

        overlay = ctk.CTkFrame(glow, fg_color="transparent", corner_radius=0)
        overlay.grid(row=0, column=0, sticky="w", padx=(26, 18))
        overlay.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            overlay,
            text="Current CSV",
            text_color=self.c("muted"),
            font=("Segoe UI Semibold", 12),
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            overlay,
            text=Path(self.csv_path.get()).name,
            text_color=self.c("text"),
            font=("Segoe UI Semibold", 24),
            justify="left",
            anchor="w",
            wraplength=700,
        ).grid(row=1, column=0, sticky="w")

        self._button(
            glow,
            text="Edit CSV",
            command=self._open_csv_editor,
            fg="#BFEAA4",
            hover="#ADD98F",
            text_color="#234119",
            width=118,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=1, sticky="e", padx=(0, 24))

        body = ctk.CTkFrame(page, fg_color="transparent", corner_radius=0)
        body.grid(row=1, column=0, sticky="ew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        bulletin = self._panel(
            body,
            title="Bulletin Maker",
            subtitle="Generate the two-column service bulletin page from the current sectioned CSV.",
            accent=self.c("green"),
            soft=self.c("green_soft"),
            border=self.c("green_border"),
        )
        bulletin.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))

        slides = self._panel(
            body,
            title="Slides Generator",
            subtitle="Choose a template from a visual gallery and generate PowerPoint slides.",
            accent=self.c("amber"),
            soft=self.c("amber_soft"),
            border=self.c("amber_border"),
        )
        slides.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        lower_thirds = self._panel(
            body,
            title="Lower Thirds",
            subtitle="Generate 1920x1080 lower thirds based on the Canva-inspired blue banner design.",
            accent=self.c("blue"),
            soft=self.c("blue_soft"),
            border=self.c("blue_border"),
        )
        lower_thirds.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 10))

        self._build_bulletin_panel(bulletin)
        self._build_slides_panel(slides)
        self._build_lower_thirds_panel(lower_thirds)

    def _build_bulletin_panel(self, parent: ctk.CTkFrame) -> None:
        self._field(parent, row=2, label="PDF output", variable=self.pdf_output_path, button_text="Save As", button_command=self._choose_pdf_output, tone="green")

        self._button(
            parent,
            text="Generate Bulletin",
            command=self._generate_pdf,
            fg=self.c("green"),
            hover=self.c("green_hover"),
            text_color="white",
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(0, 20))

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

        self._button(
            parent,
            text="Generate Lower Thirds",
            command=self._generate_lower_thirds,
            fg=self.c("blue"),
            hover=self.c("blue_hover"),
            text_color="white",
            width=180,
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(0, 20))

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
        self._apply_window_icon(window)
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

    def _make_gradient_pil(self, width: int, height: int, variant: str = "landing") -> Image.Image:
        image = Image.new("RGB", (width, height), self.c("window_bg"))
        draw = ImageDraw.Draw(image)
        if variant == "welcome":
            if self.theme_mode == "light":
                start = (24, 84, 189)
                end = (181, 102, 220)
            else:
                start = (18, 52, 121)
                end = (132, 73, 174)
        elif variant == "landing":
            if self.theme_mode == "light":
                top = (187, 225, 250)
                bottom = (251, 236, 220)
                orb_one = (121, 192, 255)
                orb_two = (255, 216, 160)
                card = "#FFFDFB"
                stroke = "#E8DDD2"
            else:
                top = (28, 39, 58)
                bottom = (33, 25, 38)
                orb_one = (56, 132, 230)
                orb_two = (214, 139, 78)
                card = "#221E1B"
                stroke = "#3A332D"
        else:
            if self.theme_mode == "light":
                top = (231, 241, 255)
                bottom = (245, 236, 228)
                orb_one = (93, 158, 255)
                orb_two = (120, 210, 181)
                card = "#FFFDFC"
                stroke = "#E7DDD2"
            else:
                top = (30, 38, 56)
                bottom = (31, 26, 36)
                orb_one = (71, 116, 221)
                orb_two = (62, 160, 141)
                card = "#25211E"
                stroke = "#3A332D"

        if variant == "welcome":
            base_w = 160
            base_h = 120
            small = Image.new("RGB", (base_w, base_h), start)
            for y in range(base_h):
                y_ratio = y / max(1, base_h - 1)
                for x in range(base_w):
                    x_ratio = x / max(1, base_w - 1)
                    mix = min(1.0, max(0.0, (x_ratio * 0.62) + (y_ratio * 0.38)))
                    color = tuple(int(start[i] + ((end[i] - start[i]) * mix)) for i in range(3))
                    small.putpixel((x, y), color)
            return small.resize((width, height), Image.Resampling.BICUBIC)

        for y in range(height):
            mix = y / max(1, height - 1)
            color = tuple(int(top[i] + ((bottom[i] - top[i]) * mix)) for i in range(3))
            draw.line((0, y, width, y), fill=color)

        for boost in (80, 45, 20):
            glow_one = tuple(min(255, channel + boost) for channel in orb_one)
            glow_two = tuple(min(255, channel + boost) for channel in orb_two)
            draw.ellipse((width - 240, -30, width + 20, 230), fill=glow_one)
            draw.ellipse((-70, height - 190, 210, height + 90), fill=glow_two)

        draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=30, outline=stroke, width=1, fill=card)
        draw.rounded_rectangle((40, 38, width - 40, 90), radius=18, fill=tuple(max(0, c - 10) for c in top))
        draw.rounded_rectangle((40, 112, width - 40, height - 40), radius=26, fill=tuple(max(0, c - 5) for c in bottom))
        return image

    def _make_gradient_image(self, width: int, height: int, variant: str = "landing") -> ctk.CTkImage:
        image = self._make_gradient_pil(width, height, variant)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))

    def _build_welcome_button_image(
        self,
        background: Image.Image,
        center_x_ratio: float,
        center_y_ratio: float,
        text: str,
        fill: str,
    ) -> Image.Image:
        width = 220
        height = 52
        center_x = int(background.width * center_x_ratio)
        center_y = int(background.height * center_y_ratio)
        left = max(0, center_x - (width // 2))
        top = max(0, center_y - (height // 2))
        right = min(background.width, left + width)
        bottom = min(background.height, top + height)

        patch = background.crop((left, top, right, bottom)).convert("RGBA")
        draw = ImageDraw.Draw(patch)
        draw.rounded_rectangle((0, 0, patch.width - 1, patch.height - 1), radius=26, fill=fill, outline="#F4F4FA", width=1)

        font_path = Path("C:/Windows/Fonts/segoeuib.ttf")
        try:
            font = ImageFont.truetype(str(font_path), 16)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (patch.width - text_width) // 2 - bbox[0]
        text_y = (patch.height - text_height) // 2 - bbox[1]
        draw.text((text_x, text_y), text, fill="#FFFFFF", font=font)
        return patch

    def _welcome_surface_color(self, x_ratio: float, y_ratio: float) -> str:
        if self.theme_mode == "light":
            start = (24, 84, 189)
            end = (181, 102, 220)
        else:
            start = (18, 52, 121)
            end = (132, 73, 174)

        mix = min(1.0, max(0.0, (x_ratio * 0.62) + (y_ratio * 0.38)))
        color = tuple(int(start[i] + ((end[i] - start[i]) * mix)) for i in range(3))
        return "#{:02X}{:02X}{:02X}".format(*color)

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
        self._prefill_outputs(path)
        self._show_actions_screen()
        self._set_status("CSV selected.", self.c("status_success"))

    def _open_program_maker(self) -> None:
        if self.program_maker_window and self.program_maker_window.window.winfo_exists():
            self.program_maker_window.window.focus()
            return

        self.program_maker_window = ProgramMakerWindow(self)

    def _open_csv_editor(self) -> None:
        csv_path = self.csv_path.get().strip()
        if not csv_path:
            messagebox.showerror("Missing CSV", "Choose a CSV file first.")
            return
        if self.program_maker_window and self.program_maker_window.window.winfo_exists():
            self.program_maker_window.window.focus()
            return

        self.program_maker_window = ProgramMakerWindow(self, mode="edit", csv_path=csv_path)

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
            self._reveal_output_path(output_path)
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
            self._reveal_output_path(output_path)
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
            self._reveal_output_path(output_dir, is_directory=True)
        except Exception as exc:
            self._set_status(f"Lower thirds generation failed: {exc}", self.c("status_error"))
            messagebox.showerror("Lower Thirds Failed", str(exc))

    def _reveal_output_path(self, output_path: str, is_directory: bool = False) -> None:
        target = Path(output_path)
        try:
            if is_directory:
                os.startfile(str(target))
                return
            subprocess.Popen(["explorer", "/select,", str(target)])
        except Exception:
            fallback = target if is_directory else target.parent
            try:
                os.startfile(str(fallback))
            except Exception:
                pass

    def _panel(self, parent, title: str, subtitle: str, accent: str, soft: str, border: str) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, fg_color=self.c("card_bg"), corner_radius=30, border_width=1, border_color=border)
        panel.grid_columnconfigure(0, weight=1)
        if title == "Bulletin Maker":
            panel.configure(height=320)
        elif title == "Slides Generator":
            panel.configure(height=640)
        elif title == "Lower Thirds":
            panel.configure(height=320)
        else:
            panel.configure(height=390)
        panel.grid_propagate(False)

        accent_bar = ctk.CTkFrame(panel, fg_color=soft, corner_radius=24, height=90)
        accent_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))
        accent_bar.grid_columnconfigure(0, weight=1)
        accent_bar.grid_rowconfigure(0, weight=1)
        accent_bar.grid_propagate(False)

        ctk.CTkLabel(
            accent_bar,
            text=title,
            text_color=accent,
            font=("Segoe UI Semibold", 24),
            anchor="center",
            justify="center",
        ).grid(row=0, column=0, sticky="nsew", padx=16)
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

    def __init__(
        self,
        app: BulletinApp,
        mode: str = "create",
        csv_path: str | None = None,
        initial_state: dict[str, object] | None = None,
    ) -> None:
        self.app = app
        self.mode = mode
        self.source_csv_path = csv_path or ""
        self.initial_state = initial_state
        self.section_time_vars: dict[str, tk.StringVar] = {
            title: tk.StringVar(value=section_time) for title, section_time in self.SECTIONS
        }
        self.window = ctk.CTkToplevel(app.root, fg_color=app.c("window_bg"))
        app._apply_window_icon(self.window)
        self.window.title("CSV Editor" if self.mode == "edit" else "Program Maker")
        self.window.geometry("1120x760")
        self.window.minsize(980, 680)
        self.window.resizable(True, True)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.saved_path = tk.StringVar()
        self.rows_by_section: dict[str, list[dict[str, object]]] = {
            title: [] for title, _ in self.SECTIONS
        }
        self.drag_state: dict[str, object] | None = None

        self._build()
        if self.initial_state is not None:
            self._load_state(self.initial_state)
        elif self.mode == "edit" and self.source_csv_path:
            self.saved_path.set(self.source_csv_path)
            self._load_csv_rows(self.source_csv_path)
        else:
            self._load_template_rows()
        self.window.after(40, self._bring_to_front)

    def _bring_to_front(self) -> None:
        if not self.window.winfo_exists():
            return
        try:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        except Exception:
            pass

    def _build(self) -> None:
        header = ctk.CTkFrame(self.window, fg_color="transparent", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header.grid_columnconfigure(1, weight=1)

        self.app._button(
            header,
            text="Back",
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
            text="CSV Editor" if self.mode == "edit" else "Program Maker",
            text_color=self.app.c("text"),
            font=("Segoe UI Semibold", 28),
        ).grid(row=0, column=1, sticky="w")

        self.app._button(
            header,
            text="Dark Mode" if self.app.theme_mode == "light" else "Light Mode",
            command=self._toggle_program_maker_theme,
            fg=self.app.c("button_soft"),
            hover=self.app.c("button_soft_hover"),
            text_color=self.app.c("text"),
            width=112,
            height=38,
            radius=18,
            font=("Segoe UI Semibold", 13),
        ).grid(row=0, column=2, sticky="e")

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
        toolbar.grid_columnconfigure(0, weight=1)

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
        ).grid(row=0, column=1, sticky="e")

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

        if self.mode != "edit":
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

    def _section_palette(self, section_title: str) -> dict[str, str]:
        if section_title == "Filipino Service":
            return {
                "accent": "#C84747",
                "soft": "#F8E2E2" if self.app.theme_mode == "light" else "#3C2424",
                "border": "#E8A2A2" if self.app.theme_mode == "light" else "#7A4444",
                "hover": "#B53C3C",
            }
        if section_title == "Sabbath School":
            return {
                "accent": "#C59A14",
                "soft": "#FBF3D8" if self.app.theme_mode == "light" else "#3D3420",
                "border": "#E8D27A" if self.app.theme_mode == "light" else "#7D6727",
                "hover": "#AE870F",
            }
        return {
            "accent": "#66B9FF",
            "soft": "#E4F2FF" if self.app.theme_mode == "light" else "#203246",
            "border": "#A7D4FF" if self.app.theme_mode == "light" else "#44759F",
            "hover": "#4FA8F1",
        }

    def _toggle_program_maker_theme(self) -> None:
        state = self._snapshot_state()
        target_mode = "dark" if self.app.theme_mode == "light" else "light"
        self.close()
        self.app._apply_theme_mode(target_mode)
        self.app.program_maker_window = ProgramMakerWindow(
            self.app,
            mode=self.mode,
            csv_path=self.saved_path.get().strip() or self.source_csv_path,
            initial_state=state,
        )

    def _build_section_panel(self, section_title: str, section_time: str) -> ctk.CTkFrame:
        palette = self._section_palette(section_title)
        accent = palette["accent"]
        soft = palette["soft"]
        border = palette["border"]

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

        title_bar = ctk.CTkFrame(top, fg_color=soft, corner_radius=18, height=38)
        title_bar.grid(row=0, column=0, sticky="ew")
        title_bar.grid_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text=section_title,
            text_color=accent,
            font=("Segoe UI Semibold", 20),
            anchor="w",
        ).place(x=20, rely=0.5, anchor="w")

        time_label = ctk.CTkLabel(
            title_bar,
            textvariable=self.section_time_vars[section_title],
            text_color=accent,
            font=("Segoe UI Semibold", 15),
            anchor="e",
        )
        time_label.place(relx=1.0, x=-20, rely=0.5, anchor="e")
        self._attach_time_editor(title_bar, time_label, section_title, soft, border)

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
            hover=palette["hover"],
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
        for section_title, section_time in self.SECTIONS:
            self.section_time_vars[section_title].set(section_time)
            for _ in range(starter_counts[section_title]):
                self._add_row(section_title)

    def _load_csv_rows(self, csv_path: str) -> None:
        sections = load_bulletin_sections(csv_path)
        for section in sections:
            self.section_time_vars[section.title].set(section.time)
            if not section.entries:
                self._add_row(section.title)
                continue
            for entry in section.entries:
                self._add_row(section.title, entry.title, entry.name, entry.extra)

    def _load_state(self, state: dict[str, object]) -> None:
        saved_path = str(state.get("saved_path", "")).strip()
        if saved_path:
            self.saved_path.set(saved_path)
        section_times = state.get("section_times", {})
        if isinstance(section_times, dict):
            for section_title, value in section_times.items():
                if section_title in self.section_time_vars:
                    self.section_time_vars[section_title].set(str(value))
        rows = state.get("rows", {})
        if isinstance(rows, dict):
            for section_title, items in rows.items():
                if section_title not in self.rows_by_section or not isinstance(items, list):
                    continue
                if not items:
                    self._add_row(section_title)
                    continue
                for item in items:
                    if isinstance(item, dict):
                        self._add_row(
                            section_title,
                            str(item.get("title", "")),
                            str(item.get("subheading", "")),
                            str(item.get("small_subheading", "")),
                        )

    def _snapshot_state(self) -> dict[str, object]:
        return {
            "saved_path": self.saved_path.get().strip(),
            "section_times": {section: var.get().strip() for section, var in self.section_time_vars.items()},
            "rows": {
                section_title: [
                    {
                        "title": str(row_data["title"].get()),
                        "subheading": str(row_data["subheading"].get()),
                        "small_subheading": str(row_data["small_subheading"].get()),
                    }
                    for row_data in self.rows_by_section[section_title]
                ]
                for section_title, _ in self.SECTIONS
            },
        }

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
        palette = self._section_palette(section_title)

        title_var = tk.StringVar(value=title)
        subheading_var = tk.StringVar(value=subheading)
        small_subheading_var = tk.StringVar(value=small_subheading)

        row_frame = ctk.CTkFrame(rows_frame, fg_color="transparent", corner_radius=0)
        row_frame.grid_columnconfigure(0, weight=4)
        row_frame.grid_columnconfigure(1, weight=3)
        row_frame.grid_columnconfigure(2, weight=3)
        row_frame.grid(row=len(self.rows_by_section[section_title]), column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self._entry_with_colors(row_frame, title_var, "Program item title", palette["soft"], palette["border"]).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._entry_with_colors(row_frame, subheading_var, "Name or subheading", palette["soft"], palette["border"]).grid(row=0, column=1, sticky="ew", padx=8)
        self._entry_with_colors(row_frame, small_subheading_var, "Extra line", palette["soft"], palette["border"]).grid(row=0, column=2, sticky="ew", padx=(8, 144))

        move_frame = ctk.CTkFrame(row_frame, fg_color="transparent", corner_radius=0)
        move_frame.grid(row=0, column=3, sticky="e", padx=(8, 8))

        row_data = {
            "frame": row_frame,
            "title": title_var,
            "subheading": subheading_var,
            "small_subheading": small_subheading_var,
            "section": section_title,
            "palette": palette,
        }

        drag_handle = ctk.CTkLabel(
            move_frame,
            text=":::",
            text_color=self.app.c("muted"),
            font=("Segoe UI Semibold", 18),
            width=28,
            cursor="hand2",
        )
        drag_handle.grid(row=0, column=0, padx=(0, 6))
        drag_handle.bind("<ButtonPress-1>", lambda event, data=row_data, section=section_title: self._start_row_drag(section, data, event))

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
        ).grid(row=0, column=4, sticky="e")

        self.rows_by_section[section_title].append(row_data)

    def _entry_with_colors(self, parent, variable: tk.StringVar, placeholder: str, soft: str, border: str) -> ctk.CTkEntry:
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

    def _remove_row(self, section_title: str, row_data: dict[str, object]) -> None:
        frame = row_data["frame"]
        if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
            frame.destroy()
        self.rows_by_section[section_title] = [row for row in self.rows_by_section[section_title] if row is not row_data]
        self._reflow_rows(section_title)

    def _start_row_drag(self, section_title: str, row_data: dict[str, object], event) -> None:
        if self.drag_state is not None:
            return

        frame = row_data["frame"]
        if not isinstance(frame, ctk.CTkFrame) or not frame.winfo_exists():
            return

        self.window.update_idletasks()
        rows = self.rows_by_section[section_title]
        try:
            index = rows.index(row_data)
        except ValueError:
            return

        palette = row_data["palette"]
        placeholder = ctk.CTkFrame(
            self.section_rows_frames[section_title],
            fg_color=palette["soft"],
            border_width=1,
            border_color=palette["border"],
            corner_radius=16,
            height=frame.winfo_height(),
        )
        placeholder.grid(row=index, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        placeholder.grid_propagate(False)

        frame.grid_remove()

        self.drag_state = {
            "section": section_title,
            "row_data": row_data,
            "placeholder": placeholder,
            "current_index": index,
        }
        self.window.bind("<B1-Motion>", self._on_row_drag_motion)
        self.window.bind("<ButtonRelease-1>", self._on_row_drag_release)
        self._reflow_rows(section_title, dragging=row_data)

    def _on_row_drag_motion(self, event) -> None:
        if not self.drag_state:
            return

        section_title = self.drag_state["section"]
        row_data = self.drag_state["row_data"]
        rows = self.rows_by_section[section_title]
        try:
            source_index = rows.index(row_data)
        except ValueError:
            return

        target_index = source_index
        closest_distance = None
        for index, candidate in enumerate(rows):
            frame = candidate["frame"]
            if candidate is row_data:
                continue
            if not isinstance(frame, ctk.CTkFrame) or not frame.winfo_exists():
                continue
            center_y = frame.winfo_rooty() + (frame.winfo_height() / 2)
            distance = abs(center_y - event.y_root)
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                target_index = index if event.y_root < center_y else index + 1

        if target_index == source_index:
            return
        item = rows.pop(source_index)
        if target_index > source_index:
            target_index -= 1
        rows.insert(target_index, item)
        self.drag_state["current_index"] = target_index
        self._reflow_rows(section_title, dragging=row_data)

    def _on_row_drag_release(self, event) -> None:
        if not self.drag_state:
            return

        section_title = self.drag_state["section"]
        row_data = self.drag_state["row_data"]
        placeholder = self.drag_state["placeholder"]
        frame = row_data["frame"]

        self.window.unbind("<B1-Motion>")
        self.window.unbind("<ButtonRelease-1>")

        if isinstance(placeholder, ctk.CTkFrame) and placeholder.winfo_exists():
            placeholder.destroy()
        if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
            frame.grid()

        self.drag_state = None
        self._reflow_rows(section_title)

    def _reflow_rows(self, section_title: str, dragging: dict[str, object] | None = None) -> None:
        placeholder_row = None
        if self.drag_state and self.drag_state.get("section") == section_title:
            placeholder_row = int(self.drag_state["current_index"])

        visible_index = 0
        for row_data in self.rows_by_section[section_title]:
            if placeholder_row is not None and visible_index == placeholder_row:
                placeholder = self.drag_state["placeholder"]
                if isinstance(placeholder, ctk.CTkFrame) and placeholder.winfo_exists():
                    placeholder.grid_configure(row=visible_index)
                visible_index += 1

            frame = row_data["frame"]
            if dragging is not None and row_data is dragging:
                continue
            if isinstance(frame, ctk.CTkFrame) and frame.winfo_exists():
                frame.grid()
                frame.grid_configure(row=visible_index)
            visible_index += 1

        if placeholder_row is not None and visible_index == placeholder_row:
            placeholder = self.drag_state["placeholder"]
            if isinstance(placeholder, ctk.CTkFrame) and placeholder.winfo_exists():
                placeholder.grid_configure(row=visible_index)

    def _attach_time_editor(self, parent: ctk.CTkFrame, label: ctk.CTkLabel, section_title: str, soft: str, border: str) -> None:
        def show_editor(_event=None):
            if not label.winfo_exists():
                return
            label.place_forget()
            entry = ctk.CTkEntry(
                parent,
                textvariable=self.section_time_vars[section_title],
                fg_color=soft,
                border_color=border,
                text_color=self.app.c("text"),
                width=110,
                height=30,
                corner_radius=14,
                font=("Segoe UI Semibold", 14),
                justify="right",
            )
            entry.place(relx=1.0, x=-14, rely=0.5, anchor="e")
            entry.focus_set()
            entry.select_range(0, "end")

            def finish(_evt=None):
                if entry.winfo_exists():
                    entry.destroy()
                if label.winfo_exists():
                    label.place(relx=1.0, x=-20, rely=0.5, anchor="e")

            entry.bind("<Return>", finish)
            entry.bind("<FocusOut>", finish)

        label.bind("<Double-Button-1>", show_editor)

    def _serialize_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for section_title, section_time in self.SECTIONS:
            rows.append(
                {
                    "title": section_title,
                    "subheading": self.section_time_vars[section_title].get().strip() or section_time,
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
        path = self.saved_path.get().strip() if self.mode == "edit" and self.saved_path.get().strip() else self._prompt_save_path()
        if not path:
            return
        self._write_csv(path)
        if self.mode == "edit":
            self.app.csv_path.set(path)
            self.app._prefill_outputs(path)
            self.app._show_actions_screen()
        self.app._set_status(f"Program CSV saved: {path}", self.app.c("status_success"))
        messagebox.showinfo("Saved", f"Program CSV saved:\n{path}", parent=self.window)

    def _save_and_use(self) -> None:
        path = self._prompt_save_path()
        if not path:
            return
        self._write_csv(path)
        self.app.csv_path.set(path)
        self.app._prefill_outputs(path)
        self.app._show_actions_screen()
        self.app._set_status(f"Program CSV ready: {path}", self.app.c("status_success"))
        self.close()

    def close(self) -> None:
        if self.window.winfo_exists():
            try:
                self.window.grab_release()
            except Exception:
                pass
            self.window.destroy()
        self.app.program_maker_window = None


def launch_gui() -> None:
    BulletinApp().run()
