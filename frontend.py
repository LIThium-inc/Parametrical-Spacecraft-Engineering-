import math as m
import tkinter as tk
from tkinter import ttk

from backend import (
    EARTH_RADIUS_KM,
    MU,
    buildBoosterSummaryForHohmannTransfer,
    calculateDeltaVHoman,
    calculateTravelTime,
    calculateVelocity,
    fuelDensity,
    oxiderDensity,
)


APP_BG = "#1b1b1d"
PANEL_BG = "#242428"
PANEL_ALT_BG = "#2d2d32"
FIELD_BG = "#303036"
TEXT_FG = "#e6e6e8"
MUTED_FG = "#aaaaaf"
ACCENT = "#5fb0ff"
SUCCESS = "#7ccf8a"
WARNING = "#ffb86b"
SCENE_BG = "#000000"
def format_seconds(seconds: float):
    total_seconds = int(round(seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds_left = divmod(remainder, 60)
    return f"{days} д {hours:02d} ч {minutes:02d} мин {seconds_left:02d} с"


class HohmannTransferDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Расчет deltaV и параметров разгонного блока")
        self.geometry("1920x1080")
        self.minsize(1280, 720)
        self.configure(bg=APP_BG)
        self.transient(master)
        self.grab_set()

        self.initial_radius_var = tk.StringVar(value="7000")
        self.target_radius_var = tk.StringVar(value="42164")
        self.status_var = tk.StringVar()
        self.scheme_var = tk.StringVar(value="2")
        self.fuel_type_var = tk.StringVar(value="LCH4")
        self.oxidizer_type_var = tk.StringVar(value="LOX")
        self.fuel_tank_type_var = tk.StringVar(value="Cylindrical")
        self.oxidizer_tank_type_var = tk.StringVar(value="Cylindrical")
        self.fuel_tank_material_var = tk.StringVar(value="AMg6")
        self.oxidizer_tank_material_var = tk.StringVar(value="AMg6")
        self.payload_mass_var = tk.StringVar(value="2500")
        self.oxidizer_ratio_var = tk.StringVar(value="3.4")
        self.tank_margin_var = tk.StringVar(value="0.08")
        self.custom_aux_systems_var = tk.StringVar(value="Telemetry:25; Power:40")
        self.single_stage_isp_var = tk.StringVar(value="360")
        self.single_stage_structure_var = tk.StringVar(value="0.12")
        self.universal_stage_isp_var = tk.StringVar(value="355")
        self.universal_stage_structure_var = tk.StringVar(value="0.11")
        self.stage1_isp_var = tk.StringVar(value="340")
        self.stage1_structure_var = tk.StringVar(value="0.14")
        self.stage2_isp_var = tk.StringVar(value="360")
        self.stage2_structure_var = tk.StringVar(value="0.10")

        self._earth_texture_cache = {}
        self._earth_image = None
        self.view_scale = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0
        self._drag_start = None
        self._is_fullscreen = False

        self.result_vars = {
            "initial_velocity": tk.StringVar(value="-"),
            "target_velocity": tk.StringVar(value="-"),
            "total_delta_v": tk.StringVar(value="-"),
            "first_burn": tk.StringVar(value="-"),
            "second_burn": tk.StringVar(value="-"),
            "semi_major_axis": tk.StringVar(value="-"),
            "travel_time": tk.StringVar(value="-"),
        }

        self._setup_theme()
        self._build_ui()
        self._bind_events()
        self._set_full_hd_view()
        self.update_results()

    def _setup_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=APP_BG, foreground=TEXT_FG, fieldbackground=FIELD_BG)
        style.configure("Dark.TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("AltPanel.TFrame", background=PANEL_ALT_BG)
        style.configure(
            "Dark.TLabel",
            background=PANEL_BG,
            foreground=TEXT_FG,
        )
        style.configure(
            "DarkHeader.TLabel",
            background=PANEL_BG,
            foreground=TEXT_FG,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "DarkSubHeader.TLabel",
            background=PANEL_BG,
            foreground=MUTED_FG,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Dark.TButton",
            background=FIELD_BG,
            foreground=TEXT_FG,
            padding=8,
            borderwidth=0,
        )
        style.map(
            "Dark.TButton",
            background=[("active", "#3b3b42")],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "Dark.TRadiobutton",
            background=PANEL_ALT_BG,
            foreground=TEXT_FG,
        )
        style.map(
            "Dark.TRadiobutton",
            background=[("active", PANEL_ALT_BG)],
            foreground=[("active", "#ffffff")],
        )
        style.configure("Dark.TCombobox", fieldbackground=FIELD_BG, foreground=TEXT_FG)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        split_frame = tk.Frame(self, bg=APP_BG)
        split_frame.grid(row=0, column=0, sticky="nsew")
        split_frame.grid_columnconfigure(0, weight=0, minsize=720)
        split_frame.grid_columnconfigure(1, weight=0, minsize=48)
        split_frame.grid_columnconfigure(2, weight=1)
        split_frame.grid_rowconfigure(0, weight=1)

        controls_host = ttk.Frame(split_frame, style="Panel.TFrame", width=720)
        controls_host.grid(row=0, column=0, sticky="nsew")
        controls_host.grid_propagate(False)
        controls_host.columnconfigure(0, weight=1)
        controls_host.rowconfigure(0, weight=1)

        self.controls_canvas = tk.Canvas(
            controls_host,
            width=720,
            bg=PANEL_BG,
            highlightthickness=0,
            bd=0,
        )
        self.controls_canvas.grid(row=0, column=0, sticky="nsew")

        controls_scrollbar = ttk.Scrollbar(
            controls_host,
            orient="vertical",
            command=self.controls_canvas.yview,
        )
        controls_scrollbar.grid(row=0, column=1, sticky="ns")
        self.controls_canvas.configure(yscrollcommand=controls_scrollbar.set)

        controls = ttk.Frame(self.controls_canvas, padding=18, style="Panel.TFrame")
        self.controls_window = self.controls_canvas.create_window(
            (0, 0),
            window=controls,
            anchor="nw",
        )

        controls.bind(
            "<Configure>",
            lambda _event: self.controls_canvas.configure(
                scrollregion=self.controls_canvas.bbox("all")
            ),
        )
        self.controls_canvas.bind("<Configure>", self._resize_controls_window)

        ttk.Label(
            controls,
            text="Параметры расчета",
            style="DarkHeader.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(
            controls,
            text="Орбиты, время перелета и схема разгонного блока",
            style="DarkSubHeader.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 16))

        orbit_panel = ttk.Frame(controls, padding=12, style="AltPanel.TFrame")
        orbit_panel.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        orbit_panel.columnconfigure(1, weight=1)
        self._build_orbit_panel(orbit_panel)

        stage_panel = ttk.Frame(controls, padding=12, style="AltPanel.TFrame")
        stage_panel.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        stage_panel.columnconfigure(1, weight=1)
        self._build_stage_panel(stage_panel)

        action_panel = ttk.Frame(controls, style="Panel.TFrame")
        action_panel.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        action_panel.columnconfigure(0, weight=1)
        action_panel.columnconfigure(1, weight=1)
        action_panel.columnconfigure(2, weight=1)

        ttk.Button(
            action_panel,
            text="Пересчитать",
            style="Dark.TButton",
            command=self.update_results,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            action_panel,
            text="Сбросить вид",
            style="Dark.TButton",
            command=self._reset_view,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        self.fullscreen_button = ttk.Button(
            action_panel,
            text="FullHD / полный экран",
            style="Dark.TButton",
            command=self._toggle_fullscreen,
        )
        self.fullscreen_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        results_panel = ttk.Frame(controls, padding=12, style="AltPanel.TFrame")
        results_panel.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        results_panel.columnconfigure(1, weight=1)
        self._build_results_panel(results_panel)

        booster_panel = ttk.Frame(controls, padding=12, style="AltPanel.TFrame")
        booster_panel.grid(row=6, column=0, columnspan=2, sticky="nsew")
        booster_panel.columnconfigure(0, weight=1)
        booster_panel.rowconfigure(1, weight=1)
        controls.rowconfigure(6, weight=1)
        self._build_booster_results_panel(booster_panel)

        tk.Label(
            controls,
            textvariable=self.status_var,
            bg=PANEL_BG,
            fg=WARNING,
            wraplength=420,
            justify="left",
            font=("Segoe UI", 9),
        ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        spacer = tk.Frame(split_frame, bg=APP_BG, width=48)
        spacer.grid(row=0, column=1, sticky="ns")
        spacer.grid_propagate(False)

        visual_frame = ttk.Frame(split_frame, padding=(24, 18, 18, 18), style="Dark.TFrame")
        visual_frame.grid(row=0, column=2, sticky="nsew")
        visual_frame.columnconfigure(0, weight=1)
        visual_frame.rowconfigure(1, weight=1)

        tk.Label(
            visual_frame,
            text="Сцена орбитального перехода",
            bg=APP_BG,
            fg=TEXT_FG,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.canvas = tk.Canvas(
            visual_frame,
            width=1180,
            height=920,
            bg=SCENE_BG,
            highlightthickness=1,
            highlightbackground="#2e2e2e",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")

    def _build_orbit_panel(self, parent: ttk.Frame):
        ttk.Label(parent, text="Орбитальные параметры", style="DarkHeader.TLabel").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )
        self._add_labeled_entry(parent, 1, "Начальный радиус, км", self.initial_radius_var)
        self._add_labeled_entry(parent, 2, "Целевой радиус, км", self.target_radius_var)
        ttk.Label(
            parent,
            text=f"Радиус Земли: {EARTH_RADIUS_KM:,.0f} км",
            style="DarkSubHeader.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_stage_panel(self, parent: ttk.Frame):
        ttk.Label(parent, text="Разгонный блок", style="DarkHeader.TLabel").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        scheme_row = ttk.Frame(parent, style="AltPanel.TFrame")
        scheme_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Radiobutton(
            scheme_row,
            text="Одна ступень",
            value="1",
            variable=self.scheme_var,
            style="Dark.TRadiobutton",
            command=self.update_results,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            scheme_row,
            text="Две ступени",
            value="2",
            variable=self.scheme_var,
            style="Dark.TRadiobutton",
            command=self.update_results,
        ).pack(side="left")
        ttk.Radiobutton(
            scheme_row,
            text="Две универсальные ступени",
            value="2u",
            variable=self.scheme_var,
            style="Dark.TRadiobutton",
            command=self.update_results,
        ).pack(side="left", padx=(16, 0))
        ttk.Radiobutton(
            scheme_row,
            text="Две стыкующиеся ступени",
            value="2d",
            variable=self.scheme_var,
            style="Dark.TRadiobutton",
            command=self.update_results,
        ).pack(side="left", padx=(16, 0))

        self._add_labeled_entry(parent, 2, "Полезная нагрузка, кг", self.payload_mass_var)
        self._add_labeled_entry(parent, 3, "Отношение O/F", self.oxidizer_ratio_var)
        self._add_labeled_entry(parent, 4, "Запас объема баков", self.tank_margin_var)
        self._add_labeled_combobox(parent, 5, "Топливо", self.fuel_type_var, list(fuelDensity.keys()))
        self._add_labeled_combobox(parent, 6, "Окислитель", self.oxidizer_type_var, list(oxiderDensity.keys()))
        self._add_labeled_combobox(parent, 7, "Тип бака топлива", self.fuel_tank_type_var, ["Spherical", "Cylindrical", "Torus"])
        self._add_labeled_combobox(parent, 8, "Тип бака окислителя", self.oxidizer_tank_type_var, ["Spherical", "Cylindrical", "Torus"])
        self._add_labeled_combobox(parent, 9, "Материал бака топлива", self.fuel_tank_material_var, ["AMg6", "Aluminum", "Titanium", "CarbonFiber"])
        self._add_labeled_combobox(parent, 10, "Материал бака окислителя", self.oxidizer_tank_material_var, ["AMg6", "Aluminum", "Titanium", "CarbonFiber"])
        self._add_labeled_entry(parent, 11, "Доп. системы (name:mass; ...)", self.custom_aux_systems_var)

        ttk.Label(
            parent,
            text="Одноступенчатая схема",
            style="DarkSubHeader.TLabel",
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(10, 4))
        self._add_labeled_entry(parent, 13, "Isp единой ступени, с", self.single_stage_isp_var)
        self._add_labeled_entry(parent, 14, "Конструктивный коэффициент", self.single_stage_structure_var)

        ttk.Label(
            parent,
            text="Две универсальные ступени",
            style="DarkSubHeader.TLabel",
        ).grid(row=15, column=0, columnspan=2, sticky="w", pady=(10, 4))
        self._add_labeled_entry(parent, 16, "Isp универсальной ступени, с", self.universal_stage_isp_var)
        self._add_labeled_entry(parent, 17, "Коэффициент универсальной ступени", self.universal_stage_structure_var)

        ttk.Label(
            parent,
            text="Двухступенчатая схема",
            style="DarkSubHeader.TLabel",
        ).grid(row=18, column=0, columnspan=2, sticky="w", pady=(10, 4))
        self._add_labeled_entry(parent, 19, "Isp ступени 1, с", self.stage1_isp_var)
        self._add_labeled_entry(parent, 20, "Коэффициент ступени 1", self.stage1_structure_var)
        self._add_labeled_entry(parent, 21, "Isp ступени 2, с", self.stage2_isp_var)
        self._add_labeled_entry(parent, 22, "Коэффициент ступени 2", self.stage2_structure_var)

    def _build_results_panel(self, parent: ttk.Frame):
        ttk.Label(parent, text="Результаты орбитального расчета", style="DarkHeader.TLabel").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )
        result_rows = [
            ("Скорость на начальной орбите", "initial_velocity"),
            ("Скорость на целевой орбите", "target_velocity"),
            ("Общий deltaV", "total_delta_v"),
            ("Первый импульс", "first_burn"),
            ("Второй импульс", "second_burn"),
            ("Большая полуось перехода", "semi_major_axis"),
            ("Время перелета", "travel_time"),
        ]

        for row_index, (label, key) in enumerate(result_rows, start=1):
            ttk.Label(parent, text=label, style="Dark.TLabel").grid(
                row=row_index,
                column=0,
                sticky="w",
                pady=3,
            )
            ttk.Label(
                parent,
                textvariable=self.result_vars[key],
                style="Dark.TLabel",
                anchor="e",
            ).grid(row=row_index, column=1, sticky="e", pady=3)

    def _build_booster_results_panel(self, parent: ttk.Frame):
        ttk.Label(parent, text="Итог по разгонному блоку", style="DarkHeader.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 10),
        )
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        self.booster_text = tk.Text(
            parent,
            height=12,
            wrap="word",
            bg="#17171a",
            fg=TEXT_FG,
            insertbackground=TEXT_FG,
            relief="flat",
            padx=12,
            pady=12,
            font=("Consolas", 10),
        )
        self.booster_text.grid(row=1, column=0, sticky="nsew")
        booster_scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.booster_text.yview,
        )
        booster_scrollbar.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        self.booster_text.configure(yscrollcommand=booster_scrollbar.set)
        self.booster_text.configure(state="disabled")

    def _add_labeled_entry(self, parent, row, text, variable):
        ttk.Label(parent, text=text, style="Dark.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg=FIELD_BG,
            fg=TEXT_FG,
            insertbackground=TEXT_FG,
            relief="flat",
            justify="right",
            width=18,
        )
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))
        return entry

    def _add_labeled_combobox(self, parent, row, text, variable, values):
        ttk.Label(parent, text=text, style="Dark.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            style="Dark.TCombobox",
        )
        combo.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.update_results())
        return combo

    def _bind_events(self):
        tracked_variables = [
            self.initial_radius_var,
            self.target_radius_var,
            self.scheme_var,
            self.payload_mass_var,
            self.oxidizer_ratio_var,
            self.tank_margin_var,
            self.fuel_type_var,
            self.oxidizer_type_var,
            self.fuel_tank_type_var,
            self.oxidizer_tank_type_var,
            self.fuel_tank_material_var,
            self.oxidizer_tank_material_var,
            self.custom_aux_systems_var,
            self.single_stage_isp_var,
            self.single_stage_structure_var,
            self.universal_stage_isp_var,
            self.universal_stage_structure_var,
            self.stage1_isp_var,
            self.stage1_structure_var,
            self.stage2_isp_var,
            self.stage2_structure_var,
        ]
        for variable in tracked_variables:
            variable.trace_add("write", self._on_input_change)

        self.canvas.bind("<Configure>", lambda _event: self.update_results())
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan_canvas)
        self.canvas.bind("<ButtonRelease-1>", self._stop_pan)
        self.canvas.bind("<MouseWheel>", self._zoom_canvas)
        self.canvas.bind("<Button-4>", self._zoom_canvas)
        self.canvas.bind("<Button-5>", self._zoom_canvas)
        self.controls_canvas.bind("<MouseWheel>", self._scroll_controls_panel)
        self.controls_canvas.bind("<Button-4>", self._scroll_controls_panel)
        self.controls_canvas.bind("<Button-5>", self._scroll_controls_panel)
        self.booster_text.bind("<MouseWheel>", self._scroll_booster_results)
        self.booster_text.bind("<Button-4>", self._scroll_booster_results)
        self.booster_text.bind("<Button-5>", self._scroll_booster_results)
        self.bind("<F11>", lambda _event: self._toggle_fullscreen())
        self.bind("<Escape>", lambda _event: self._exit_fullscreen())

    def _resize_controls_window(self, event):
        self.controls_canvas.itemconfigure(self.controls_window, width=event.width)

    def _set_full_hd_view(self):
        self.geometry("1920x1080+0+0")
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

    def _toggle_fullscreen(self):
        self._is_fullscreen = not self._is_fullscreen
        self.attributes("-fullscreen", self._is_fullscreen)
        if not self._is_fullscreen:
            self._set_full_hd_view()

    def _exit_fullscreen(self):
        if self._is_fullscreen:
            self._toggle_fullscreen()

    def _on_input_change(self, *_args):
        self.update_results()

    def _reset_view(self):
        self.view_scale = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0
        self.update_results()

    def _start_pan(self, event):
        self._drag_start = (event.x, event.y)

    def _pan_canvas(self, event):
        if self._drag_start is None:
            self._drag_start = (event.x, event.y)
            return
        self.view_offset_x += event.x - self._drag_start[0]
        self.view_offset_y += event.y - self._drag_start[1]
        self._drag_start = (event.x, event.y)
        self.update_results()

    def _stop_pan(self, _event):
        self._drag_start = None

    def _zoom_canvas(self, event):
        if hasattr(event, "delta") and event.delta:
            zoom_factor = 1.1 if event.delta > 0 else 1 / 1.1
        elif getattr(event, "num", None) == 4:
            zoom_factor = 1.1
        else:
            zoom_factor = 1 / 1.1

        previous_scale = self.view_scale
        new_scale = min(25.0, max(0.2, previous_scale * zoom_factor))
        if abs(new_scale - previous_scale) < 1e-9:
            return

        width = self.canvas.winfo_width() or 1180
        height = self.canvas.winfo_height() or 920
        scene_x = (event.x - width / 2 - self.view_offset_x) / previous_scale
        scene_y = (event.y - height / 2 - self.view_offset_y) / previous_scale

        self.view_scale = new_scale
        self.view_offset_x = event.x - width / 2 - scene_x * self.view_scale
        self.view_offset_y = event.y - height / 2 - scene_y * self.view_scale
        self.update_results()

    def _scroll_controls_panel(self, event):
        self._scroll_widget(self.controls_canvas, event)

    def _scroll_booster_results(self, event):
        self._scroll_widget(self.booster_text, event)
        return "break"

    def _scroll_widget(self, widget, event):
        if hasattr(event, "delta") and event.delta:
            step = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            step = -1
        else:
            step = 1
        widget.yview_scroll(step, "units")
        return "break"

    def _parse_positive_float(self, raw_value: str, field_name: str):
        normalized = raw_value.replace(",", ".").strip()
        value = float(normalized)
        if value <= 0:
            raise ValueError(f"{field_name} должен быть больше нуля.")
        return value

    def _parse_ratio(self, raw_value: str, field_name: str):
        value = self._parse_positive_float(raw_value, field_name)
        if value >= 1 and "коэффициент" in field_name.lower():
            raise ValueError(f"{field_name} должен быть меньше 1.")
        return value

    def _parse_non_negative_float(self, raw_value: str, field_name: str):
        normalized = raw_value.replace(",", ".").strip()
        value = float(normalized)
        if value < 0:
            raise ValueError(f"{field_name} не может быть отрицательным.")
        return value

    def _parse_custom_auxiliary_systems(self, raw_value: str):
        raw_text = raw_value.strip()
        if not raw_text:
            return []

        systems = []
        parts = [part.strip() for part in raw_text.split(";") if part.strip()]
        for part in parts:
            if ":" not in part:
                raise ValueError(
                    "Доп. системы нужно вводить в формате name:mass; name:mass"
                )
            name, mass_text = part.split(":", 1)
            system_name = name.strip()
            if not system_name:
                raise ValueError("Название вспомогательной системы не может быть пустым.")
            system_mass = self._parse_non_negative_float(
                mass_text.strip(),
                f"Масса системы {system_name}",
            )
            systems.append((system_name, system_mass))
        return systems

    def update_results(self):
        try:
            orbit_data = self._compute_orbit_data()
            booster_scheme = self._compute_booster_data(orbit_data)
        except ValueError as error:
            self.status_var.set(str(error))
            self._set_empty_results()
            self._render_booster_results([])
            self._draw_placeholder()
            return

        self.status_var.set("")
        self._fill_orbit_results(orbit_data)
        self._render_booster_results(booster_scheme)
        self._draw_orbits(orbit_data)

    def _compute_orbit_data(self):
        initial_radius_km = self._parse_positive_float(
            self.initial_radius_var.get(),
            "Начальный радиус",
        )
        target_radius_km = self._parse_positive_float(
            self.target_radius_var.get(),
            "Целевой радиус",
        )
        if initial_radius_km <= EARTH_RADIUS_KM:
            raise ValueError(
                f"Начальный радиус должен быть больше радиуса Земли ({EARTH_RADIUS_KM:,.0f} км)."
            )
        if target_radius_km <= EARTH_RADIUS_KM:
            raise ValueError(
                f"Целевой радиус должен быть больше радиуса Земли ({EARTH_RADIUS_KM:,.0f} км)."
            )

        initial_radius_m = initial_radius_km * 1000
        target_radius_m = target_radius_km * 1000
        semi_major_axis_m = (initial_radius_m + target_radius_m) / 2

        initial_velocity = calculateVelocity(initial_radius_m, initial_radius_m)
        target_velocity = calculateVelocity(target_radius_m, target_radius_m)
        total_delta_v, first_burn, second_burn = calculateDeltaVHoman(
            initial_radius_m,
            target_radius_m,
        )
        travel_time = calculateTravelTime(semi_major_axis_m, MU)

        return {
            "initial_radius_km": initial_radius_km,
            "target_radius_km": target_radius_km,
            "semi_major_axis_km": semi_major_axis_m / 1000,
            "initial_velocity": initial_velocity,
            "target_velocity": target_velocity,
            "total_delta_v": total_delta_v,
            "first_burn": first_burn,
            "second_burn": second_burn,
            "travel_time": travel_time,
        }

    def _compute_booster_data(self, orbit_data):
        payload_mass = self._parse_positive_float(self.payload_mass_var.get(), "Полезная нагрузка")
        oxidizer_to_fuel_ratio = self._parse_positive_float(
            self.oxidizer_ratio_var.get(),
            "Отношение O/F",
        )
        tank_margin_ratio = self._parse_non_negative_float(
            self.tank_margin_var.get(),
            "Запас объема баков",
        )
        scheme_type = self.scheme_var.get()
        fuel_type = self.fuel_type_var.get()
        oxidizer_type = self.oxidizer_type_var.get()
        fuel_tank_type = self.fuel_tank_type_var.get()
        oxidizer_tank_type = self.oxidizer_tank_type_var.get()
        fuel_tank_material = self.fuel_tank_material_var.get()
        oxidizer_tank_material = self.oxidizer_tank_material_var.get()
        custom_auxiliary_systems = self._parse_custom_auxiliary_systems(
            self.custom_aux_systems_var.get()
        )

        if scheme_type == "1":
            single_stage_isp = self._parse_positive_float(
                self.single_stage_isp_var.get(),
                "Isp единой ступени",
            )
            single_stage_structural_ratio = self._parse_ratio(
                self.single_stage_structure_var.get(),
                "Конструктивный коэффициент единой ступени",
            )
            summary = buildBoosterSummaryForHohmannTransfer(
                payloadMass=payload_mass,
                specificImpulse=single_stage_isp,
                deltaV=orbit_data["total_delta_v"],
                firstBurnVelocity=orbit_data["first_burn"],
                secondBurnVelocity=orbit_data["second_burn"],
                constructionMassRatio=single_stage_structural_ratio,
                oxidezerFuelMassRatio=oxidizer_to_fuel_ratio,
                fuelType=fuel_type,
                oxidizerType=oxidizer_type,
                oxidezerTankType=oxidizer_tank_type,
                fuelTankType=fuel_tank_type,
                fuelTankMaterial=fuel_tank_material,
                oxidizerTankMaterial=oxidizer_tank_material,
                stageCount=1,
                useUniversalStage=False,
                useDocking=False,
                gasCashionRatio=tank_margin_ratio,
                customAuxiliarySystems=custom_auxiliary_systems,
            )
            self._validate_booster_summary(summary)
            return summary

        if scheme_type == "2u":
            universal_stage_isp = self._parse_positive_float(
                self.universal_stage_isp_var.get(),
                "Isp универсальной ступени",
            )
            universal_stage_structural_ratio = self._parse_ratio(
                self.universal_stage_structure_var.get(),
                "Конструктивный коэффициент универсальной ступени",
            )
            summary = buildBoosterSummaryForHohmannTransfer(
                payloadMass=payload_mass,
                specificImpulse=universal_stage_isp,
                deltaV=orbit_data["total_delta_v"],
                firstBurnVelocity=orbit_data["first_burn"],
                secondBurnVelocity=orbit_data["second_burn"],
                constructionMassRatio=universal_stage_structural_ratio,
                oxidezerFuelMassRatio=oxidizer_to_fuel_ratio,
                fuelType=fuel_type,
                oxidizerType=oxidizer_type,
                oxidezerTankType=oxidizer_tank_type,
                fuelTankType=fuel_tank_type,
                fuelTankMaterial=fuel_tank_material,
                oxidizerTankMaterial=oxidizer_tank_material,
                stageCount=2,
                useUniversalStage=True,
                useDocking=False,
                universalSpecificImpulse=universal_stage_isp,
                universalConstructionMassRatio=universal_stage_structural_ratio,
                gasCashionRatio=tank_margin_ratio,
                customAuxiliarySystems=custom_auxiliary_systems,
            )
            self._validate_booster_summary(summary)
            return summary

        if scheme_type == "2d":
            universal_stage_isp = self._parse_positive_float(
                self.universal_stage_isp_var.get(),
                "Isp универсальной ступени",
            )
            universal_stage_structural_ratio = self._parse_ratio(
                self.universal_stage_structure_var.get(),
                "Конструктивный коэффициент универсальной ступени",
            )
            summary = buildBoosterSummaryForHohmannTransfer(
                payloadMass=payload_mass,
                specificImpulse=universal_stage_isp,
                deltaV=orbit_data["total_delta_v"],
                firstBurnVelocity=orbit_data["first_burn"],
                secondBurnVelocity=orbit_data["second_burn"],
                constructionMassRatio=universal_stage_structural_ratio,
                oxidezerFuelMassRatio=oxidizer_to_fuel_ratio,
                fuelType=fuel_type,
                oxidizerType=oxidizer_type,
                oxidezerTankType=oxidizer_tank_type,
                fuelTankType=fuel_tank_type,
                fuelTankMaterial=fuel_tank_material,
                oxidizerTankMaterial=oxidizer_tank_material,
                stageCount=2,
                useUniversalStage=True,
                useDocking=True,
                universalSpecificImpulse=universal_stage_isp,
                universalConstructionMassRatio=universal_stage_structural_ratio,
                gasCashionRatio=tank_margin_ratio,
                customAuxiliarySystems=custom_auxiliary_systems,
            )
            self._validate_booster_summary(summary)
            return summary

        stage1_isp = self._parse_positive_float(self.stage1_isp_var.get(), "Isp ступени 1")
        stage1_structural_ratio = self._parse_ratio(
            self.stage1_structure_var.get(),
            "Конструктивный коэффициент ступени 1",
        )
        stage2_isp = self._parse_positive_float(self.stage2_isp_var.get(), "Isp ступени 2")
        stage2_structural_ratio = self._parse_ratio(
            self.stage2_structure_var.get(),
            "Конструктивный коэффициент ступени 2",
        )

        summary = buildBoosterSummaryForHohmannTransfer(
            payloadMass=payload_mass,
            specificImpulse=stage1_isp,
            deltaV=orbit_data["total_delta_v"],
            firstBurnVelocity=orbit_data["first_burn"],
            secondBurnVelocity=orbit_data["second_burn"],
            constructionMassRatio=stage1_structural_ratio,
            oxidezerFuelMassRatio=oxidizer_to_fuel_ratio,
            fuelType=fuel_type,
            oxidizerType=oxidizer_type,
            oxidezerTankType=oxidizer_tank_type,
            fuelTankType=fuel_tank_type,
            fuelTankMaterial=fuel_tank_material,
            oxidizerTankMaterial=oxidizer_tank_material,
            stageCount=2,
            useUniversalStage=False,
            useDocking=False,
            stage1SpecificImpulse=stage1_isp,
            stage2SpecificImpulse=stage2_isp,
            stage1ConstructionMassRatio=stage1_structural_ratio,
            stage2ConstructionMassRatio=stage2_structural_ratio,
            gasCashionRatio=tank_margin_ratio,
            customAuxiliarySystems=custom_auxiliary_systems,
        )
        self._validate_booster_summary(summary)
        return summary

    def _validate_booster_summary(self, summary):
        remaining_mass = summary["remaining_auxiliary_mass"]
        if remaining_mass is not None and remaining_mass < 0:
            raise ValueError(
                "Заданной стартовой массы РБ недостаточно для размещения топлива, "
                "полезной нагрузки и уже учтенных вспомогательных систем."
            )

    def _fill_orbit_results(self, orbit_data):
        self.result_vars["initial_velocity"].set(f"{orbit_data['initial_velocity']:,.2f} м/с")
        self.result_vars["target_velocity"].set(f"{orbit_data['target_velocity']:,.2f} м/с")
        self.result_vars["total_delta_v"].set(f"{orbit_data['total_delta_v']:,.2f} м/с")
        self.result_vars["first_burn"].set(f"{orbit_data['first_burn']:,.2f} м/с")
        self.result_vars["second_burn"].set(f"{orbit_data['second_burn']:,.2f} м/с")
        self.result_vars["semi_major_axis"].set(f"{orbit_data['semi_major_axis_km']:,.2f} км")
        self.result_vars["travel_time"].set(format_seconds(orbit_data["travel_time"]))

    def _set_empty_results(self):
        for variable in self.result_vars.values():
            variable.set("-")

    def _render_booster_results(self, booster_summary):
        self.booster_text.configure(state="normal")
        self.booster_text.delete("1.0", "end")

        if not booster_summary:
            self.booster_text.insert("end", "Нет данных для отображения.")
            self.booster_text.configure(state="disabled")
            return

        header = [
            f"Схема: {self._get_scheme_label()}",
            f"Расчетная стартовая масса РБ: {booster_summary['start_mass']:,.1f} кг",
            f"Полезная нагрузка: {booster_summary['payload_mass']:,.1f} кг",
            f"Суммарная масса топлива и окислителя: {booster_summary['total_propellant_mass']:,.1f} кг",
            f"Суммарная конструктивная масса: {booster_summary['total_construction_mass']:,.1f} кг",
            f"Масса встроенных вспомогательных систем: {booster_summary['existing_auxiliary_mass']:,.1f} кг",
            f"Масса пользовательских вспомогательных систем: {booster_summary['custom_auxiliary_mass']:,.1f} кг",
            f"Остаток массы под вспомогательные системы: {booster_summary['remaining_auxiliary_mass']:,.1f} кг",
            "",
        ]
        self.booster_text.insert("end", "\n".join(header))

        if booster_summary["custom_auxiliary_systems"]:
            custom_lines = ["Пользовательские вспомогательные системы:"]
            for name, mass in booster_summary["custom_auxiliary_systems"]:
                custom_lines.append(f"  {name}: {mass:,.1f} кг")
            custom_lines.append("")
            self.booster_text.insert("end", "\n".join(custom_lines))

        for stage in booster_summary["stages"]:
            auxiliary_systems = ", ".join(
                f"{name}: {mass:,.1f} кг" for name, mass in stage["auxiliary_systems"]
            ) or "нет"
            lines = [
                f"{stage['name']} ({stage['assigned_burn']})",
                f"  Требуемый deltaV: {stage['required_delta_v']:,.2f} м/с",
                f"  Удельный импульс: {stage['specific_impulse']:,.1f} с",
                f"  Массовое число: {stage['mass_ratio']:,.3f}",
                f"  Полная масса ступени: {stage['total_stage_mass']:,.1f} кг",
                f"  Полезная нагрузка для ступени: {stage['payload_mass']:,.1f} кг",
                f"  Конструктивная масса: {stage['construction_mass']:,.1f} кг",
                f"  Дополнительные системы: {auxiliary_systems}",
                f"  Масса компонентов: {stage['total_propellant_mass']:,.1f} кг",
                f"  Топливо: {stage['fuel_mass']:,.1f} кг",
                f"  Окислитель: {stage['oxidizer_mass']:,.1f} кг",
                f"  Материал бака топлива: {stage['fuel_tank_material']}",
                f"  Материал бака окислителя: {stage['oxidizer_tank_material']}",
                f"  Объем бака топлива: {stage['fuel_tank_volume']:,.3f} м^3",
                f"  Объем бака окислителя: {stage['oxidizer_tank_volume']:,.3f} м^3",
                f"  Остаток конструктивной массы: {stage['remaining_construction_mass']:,.1f} кг",
                "",
            ]
            self.booster_text.insert("end", "\n".join(lines))

        self.booster_text.configure(state="disabled")

    def _get_scheme_label(self):
        scheme_labels = {
            "1": "одноступенчатая",
            "2": "двухступенчатая",
            "2u": "две универсальные ступени",
            "2d": "две стыкующиеся ступени",
        }
        return scheme_labels.get(self.scheme_var.get(), "неизвестная схема")

    def _draw_placeholder(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width() or 1180
        height = self.canvas.winfo_height() or 920
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Введите корректные параметры расчета",
            fill="#bcbcc2",
            font=("Segoe UI", 14, "bold"),
        )

    def _draw_orbits(self, orbit_data):
        self.canvas.delete("all")
        width = self.canvas.winfo_width() or 1180
        height = self.canvas.winfo_height() or 920
        center_x = width / 2 + self.view_offset_x
        center_y = height / 2 + self.view_offset_y

        padding = 72
        max_radius_km = max(orbit_data["initial_radius_km"], orbit_data["target_radius_km"])
        base_scale = (min(width, height) / 2 - padding) / max_radius_km
        scale = base_scale * self.view_scale

        earth_radius_px = EARTH_RADIUS_KM * scale
        scaled_initial = orbit_data["initial_radius_km"] * scale
        scaled_target = orbit_data["target_radius_km"] * scale
        scaled_perigee = min(orbit_data["initial_radius_km"], orbit_data["target_radius_km"]) * scale
        scaled_apogee = max(orbit_data["initial_radius_km"], orbit_data["target_radius_km"]) * scale
        semi_major_px = (scaled_perigee + scaled_apogee) / 2
        focal_offset_px = (scaled_apogee - scaled_perigee) / 2
        semi_minor_px = m.sqrt(max(semi_major_px**2 - focal_offset_px**2, 0))
        transfer_to_outer_orbit = orbit_data["target_radius_km"] >= orbit_data["initial_radius_km"]

        self._draw_earth(center_x, center_y, earth_radius_px)
        self._draw_circle(center_x, center_y, scaled_initial, "#55b8ff", 2)
        self._draw_circle(center_x, center_y, scaled_target, "#7bd88f", 2)
        self._draw_transfer_arc(
            center_x,
            center_y,
            semi_major_px,
            semi_minor_px,
            focal_offset_px,
            transfer_to_outer_orbit,
        )
        self._draw_burn_markers(
            center_x,
            center_y,
            scaled_initial,
            scaled_target,
            orbit_data["first_burn"],
            orbit_data["second_burn"],
            transfer_to_outer_orbit,
        )

        self.canvas.create_text(
            center_x,
            center_y + earth_radius_px + 18,
            text="Земля",
            fill="#d0d0d5",
            font=("Segoe UI", 9, "bold"),
        )
        self._draw_legend(width)

    def _draw_transfer_arc(
        self,
        center_x: float,
        center_y: float,
        semi_major_px: float,
        semi_minor_px: float,
        focal_offset_px: float,
        transfer_to_outer_orbit: bool,
    ):
        points = []
        steps = 200

        if transfer_to_outer_orbit:
            start_angle = m.pi
            end_angle = 0.0
            ellipse_center_x = center_x + focal_offset_px
            direction = -1
        else:
            start_angle = 0.0
            end_angle = m.pi
            ellipse_center_x = center_x - focal_offset_px
            direction = 1

        for step in range(steps + 1):
            progress = step / steps
            angle = start_angle + (end_angle - start_angle) * progress
            x = ellipse_center_x + semi_major_px * m.cos(angle)
            y = center_y + direction * semi_minor_px * m.sin(angle)
            points.extend((x, y))

        self.canvas.create_line(*points, fill="#ff8a66", width=2, smooth=True)

    def _draw_burn_markers(
        self,
        center_x: float,
        center_y: float,
        scaled_initial: float,
        scaled_target: float,
        first_burn_delta_v: float,
        second_burn_delta_v: float,
        transfer_to_outer_orbit: bool,
    ):
        if transfer_to_outer_orbit:
            first_point = (center_x - scaled_initial, center_y)
            second_point = (center_x + scaled_target, center_y)
            first_anchor = "ne"
            second_anchor = "sw"
            first_text_offset = (-14, -14)
            second_text_offset = (14, 14)
        else:
            first_point = (center_x + scaled_initial, center_y)
            second_point = (center_x - scaled_target, center_y)
            first_anchor = "nw"
            second_anchor = "se"
            first_text_offset = (14, -14)
            second_text_offset = (-14, 14)

        self._draw_burn_marker(
            x=first_point[0],
            y=first_point[1],
            color="#f7d26c",
            title="Первое включение",
            delta_v=first_burn_delta_v,
            anchor=first_anchor,
            text_offset=first_text_offset,
        )
        self._draw_burn_marker(
            x=second_point[0],
            y=second_point[1],
            color="#ff9f6e",
            title="Второе включение",
            delta_v=second_burn_delta_v,
            anchor=second_anchor,
            text_offset=second_text_offset,
        )

    def _draw_burn_marker(self, x, y, color, title, delta_v, anchor, text_offset):
        marker_radius = 5
        self.canvas.create_oval(
            x - marker_radius,
            y - marker_radius,
            x + marker_radius,
            y + marker_radius,
            fill=color,
            outline="#ffffff",
            width=1,
        )
        self.canvas.create_text(
            x + text_offset[0],
            y + text_offset[1],
            text=f"{title}\nΔV: {delta_v:,.2f} м/с",
            fill="#f0ead4",
            anchor=anchor,
            justify="left",
            font=("Segoe UI", 9, "bold"),
        )

    def _draw_earth(self, center_x: float, center_y: float, earth_radius_px: float):
        diameter = max(10, int(round(earth_radius_px * 2)))
        if diameter >= 18:
            self._earth_image = self._get_earth_texture(diameter)
            self.canvas.create_image(center_x, center_y, image=self._earth_image)
            self.canvas.create_oval(
                center_x - earth_radius_px,
                center_y - earth_radius_px,
                center_x + earth_radius_px,
                center_y + earth_radius_px,
                outline="#d8f0ff",
                width=1,
            )
        else:
            self.canvas.create_oval(
                center_x - earth_radius_px,
                center_y - earth_radius_px,
                center_x + earth_radius_px,
                center_y + earth_radius_px,
                fill="#366eb5",
                outline="#d8f0ff",
                width=1,
            )

    def _get_earth_texture(self, diameter: int):
        cached = self._earth_texture_cache.get(diameter)
        if cached is not None:
            return cached

        radius = diameter / 2
        image = tk.PhotoImage(width=diameter, height=diameter)
        background = self.canvas["bg"]

        for y in range(diameter):
            row = []
            for x in range(diameter):
                dx = (x + 0.5 - radius) / radius
                dy = (y + 0.5 - radius) / radius
                distance = m.sqrt(dx * dx + dy * dy)

                if distance > 1:
                    row.append(background)
                    continue

                ocean_mix = 0.55 + 0.45 * (1 - distance)
                r = int(16 + 18 * ocean_mix)
                g = int(68 + 72 * ocean_mix)
                b = int(122 + 90 * ocean_mix)

                land_noise = (
                    m.sin(dx * 7.5)
                    + m.cos(dy * 8.0)
                    + m.sin((dx + dy) * 11.0)
                    + 0.6 * m.cos(m.atan2(dy, dx) * 5.0)
                )
                if land_noise > 1.15:
                    r = int(62 + 40 * (1 - distance))
                    g = int(126 + 62 * (1 - distance))
                    b = int(67 + 26 * (1 - distance))

                cap_strength = max(0.0, (0.38 - distance) / 0.38)
                if cap_strength > 0:
                    blend = min(1.0, 0.65 + cap_strength * 0.35)
                    r = int(r * (1 - blend) + 242 * blend)
                    g = int(g * (1 - blend) + 248 * blend)
                    b = int(b * (1 - blend) + 250 * blend)

                light = 0.82 + 0.18 * (1 - ((dx + 0.3) ** 2 + (dy + 0.25) ** 2) / 1.8)
                r = max(0, min(255, int(r * light)))
                g = max(0, min(255, int(g * light)))
                b = max(0, min(255, int(b * light)))
                row.append(f"#{r:02x}{g:02x}{b:02x}")

            image.put("{" + " ".join(row) + "}", to=(0, y))

        self._earth_texture_cache[diameter] = image
        return image

    def _draw_circle(self, center_x: float, center_y: float, radius: float, color: str, width: int):
        self.canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline=color,
            width=width,
        )

    def _draw_legend(self, canvas_width: float):
        legend_items = [
            ("#55b8ff", "Начальная орбита"),
            ("#7bd88f", "Целевая орбита"),
            ("#ff8a66", "Переходная орбита"),
        ]

        x = canvas_width - 225
        y = 30
        for color, text in legend_items:
            self.canvas.create_line(x, y, x + 26, y, fill=color, width=3)
            self.canvas.create_text(
                x + 36,
                y,
                text=text,
                fill="#d8d8dd",
                anchor="w",
                font=("Segoe UI", 10),
            )
            y += 26


def open_calculation_dialog(master: tk.Misc):
    HohmannTransferDialog(master)


def main():
    root = tk.Tk()
    root.title("Расчет орбитальных маневров")
    root.geometry("1920x1080")
    root.configure(bg=APP_BG)
    try:
        root.state("zoomed")
    except tk.TclError:
        pass

    wrapper = tk.Frame(root, bg=APP_BG, padx=24, pady=24)
    wrapper.pack(fill="both", expand=True)

    tk.Label(
        wrapper,
        text="Расчет deltaV, времени перелета и параметров разгонного блока",
        bg=APP_BG,
        fg=TEXT_FG,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", pady=(0, 8))

    tk.Label(
        wrapper,
        text=(
            "Откройте расчетное окно для ввода орбитальных параметров, выбора одно- "
            "или двухступенчатой схемы и получения параметров разгонного блока."
        ),
        bg=APP_BG,
        fg=MUTED_FG,
        justify="left",
        wraplength=760,
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(0, 18))

    tk.Button(
        wrapper,
        text="Открыть окно расчета",
        bg=FIELD_BG,
        fg=TEXT_FG,
        activebackground="#3b3b42",
        activeforeground="#ffffff",
        relief="flat",
        padx=16,
        pady=10,
        command=lambda: open_calculation_dialog(root),
    ).pack(anchor="w")

    open_calculation_dialog(root)
    root.mainloop()


if __name__ == "__main__":
    main()
