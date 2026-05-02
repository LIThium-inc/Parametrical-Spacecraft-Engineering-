import math as m
import tkinter as tk
from tkinter import ttk

from backend import (
    EARTH_RADIUS_KM,
    calculateDeltaVHoman,
    calculateVelocity,
)


class HohmannTransferDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Расчет deltaV для Гомановского перехода")
        self.geometry("980x660")
        self.minsize(920, 620)
        self.transient(master)
        self.grab_set()

        self.initial_radius_var = tk.StringVar(value="7000")
        self.target_radius_var = tk.StringVar(value="12000")
        self.status_var = tk.StringVar()
        self._earth_texture_cache = {}
        self._earth_image = None
        self.view_scale = 1.0
        self.view_offset_x = 0.0
        self.view_offset_y = 0.0
        self._drag_start = None

        self.result_vars = {
            "initial_velocity": tk.StringVar(value="-"),
            "target_velocity": tk.StringVar(value="-"),
            "total_delta_v": tk.StringVar(value="-"),
            "first_burn": tk.StringVar(value="-"),
            "second_burn": tk.StringVar(value="-"),
            "semi_major_axis": tk.StringVar(value="-"),
        }

        self._build_ui()
        self._bind_events()
        self.update_results()

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=16)
        controls.grid(row=0, column=0, sticky="ns")

        ttk.Label(
            controls,
            text="Параметры орбит",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(controls, text="Начальный радиус, км").grid(
            row=1, column=0, sticky="w", pady=4
        )
        initial_entry = ttk.Entry(
            controls,
            textvariable=self.initial_radius_var,
            width=20,
            justify="right",
        )
        initial_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(controls, text="Целевой радиус, км").grid(
            row=2, column=0, sticky="w", pady=4
        )
        target_entry = ttk.Entry(
            controls,
            textvariable=self.target_radius_var,
            width=20,
            justify="right",
        )
        target_entry.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(
            controls,
            text=f"Радиус Земли: {EARTH_RADIUS_KM:,.0f} км",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 10))

        ttk.Button(
            controls,
            text="Пересчитать",
            command=self.update_results,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 16))

        ttk.Button(
            controls,
            text="Сбросить вид",
            command=self._reset_view,
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        ttk.Separator(controls, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(0, 16)
        )

        ttk.Label(
            controls,
            text="Результаты функций",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 10))

        result_rows = [
            ("Скорость на начальной орбите", "initial_velocity"),
            ("Скорость на целевой орбите", "target_velocity"),
            ("Общий deltaV", "total_delta_v"),
            ("Первый импульс", "first_burn"),
            ("Второй импульс", "second_burn"),
            ("Большая полуось перехода", "semi_major_axis"),
        ]

        for row_index, (label, key) in enumerate(result_rows, start=8):
            ttk.Label(controls, text=label).grid(
                row=row_index, column=0, sticky="w", pady=3
            )
            ttk.Label(
                controls,
                textvariable=self.result_vars[key],
                width=18,
                anchor="e",
            ).grid(row=row_index, column=1, sticky="e", pady=3)

        ttk.Label(
            controls,
            textvariable=self.status_var,
            foreground="#9c1c1c",
            wraplength=280,
        ).grid(row=20, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        visual_frame = ttk.Frame(self, padding=(0, 16, 16, 16))
        visual_frame.grid(row=0, column=1, sticky="nsew")
        visual_frame.columnconfigure(0, weight=1)
        visual_frame.rowconfigure(1, weight=1)

        ttk.Label(
            visual_frame,
            text="Визуализация орбит",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.canvas = tk.Canvas(
            visual_frame,
            width=620,
            height=560,
            bg="#07111f",
            highlightthickness=1,
            highlightbackground="#32435c",
        )
        self.canvas.grid(row=1, column=0, sticky="nsew")

        initial_entry.focus_set()

    def _bind_events(self):
        self.initial_radius_var.trace_add("write", self._on_input_change)
        self.target_radius_var.trace_add("write", self._on_input_change)
        self.canvas.bind("<Configure>", lambda _event: self.update_results())
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan_canvas)
        self.canvas.bind("<ButtonRelease-1>", self._stop_pan)
        self.canvas.bind("<MouseWheel>", self._zoom_canvas)
        self.canvas.bind("<Button-4>", self._zoom_canvas)
        self.canvas.bind("<Button-5>", self._zoom_canvas)

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

        delta_x = event.x - self._drag_start[0]
        delta_y = event.y - self._drag_start[1]
        self._drag_start = (event.x, event.y)
        self.view_offset_x += delta_x
        self.view_offset_y += delta_y
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

        width = self.canvas.winfo_width() or 620
        height = self.canvas.winfo_height() or 560
        scene_x = (event.x - width / 2 - self.view_offset_x) / previous_scale
        scene_y = (event.y - height / 2 - self.view_offset_y) / previous_scale

        self.view_scale = new_scale
        self.view_offset_x = event.x - width / 2 - scene_x * self.view_scale
        self.view_offset_y = event.y - height / 2 - scene_y * self.view_scale
        self.update_results()

    def _parse_positive_float(self, raw_value: str, field_name: str) -> float:
        normalized = raw_value.replace(",", ".").strip()
        value = float(normalized)
        if value <= 0:
            raise ValueError(f"{field_name} должен быть больше нуля.")
        return value

    def update_results(self):
        try:
            initial_radius_km = self._parse_positive_float(
                self.initial_radius_var.get(),
                "Начальный радиус",
            )
            target_radius_km = self._parse_positive_float(
                self.target_radius_var.get(),
                "Целевой радиус",
            )
            self._validate_radius(initial_radius_km, "Начальный радиус")
            self._validate_radius(target_radius_km, "Целевой радиус")
        except ValueError as error:
            self.status_var.set(str(error))
            self._set_empty_results()
            self._draw_placeholder()
            return

        self.status_var.set("")

        initial_radius_m = initial_radius_km * 1000
        target_radius_m = target_radius_km * 1000

        initial_velocity = calculateVelocity(initial_radius_m, initial_radius_m)
        target_velocity = calculateVelocity(target_radius_m, target_radius_m)
        delta_v, first_burn, second_burn = calculateDeltaVHoman(
            initial_radius_m,
            target_radius_m,
        )
        semi_major_axis_km = (initial_radius_km + target_radius_km) / 2

        self.result_vars["initial_velocity"].set(f"{initial_velocity:,.2f} м/с")
        self.result_vars["target_velocity"].set(f"{target_velocity:,.2f} м/с")
        self.result_vars["total_delta_v"].set(f"{delta_v:,.2f} м/с")
        self.result_vars["first_burn"].set(f"{first_burn:,.2f} м/с")
        self.result_vars["second_burn"].set(f"{second_burn:,.2f} м/с")
        self.result_vars["semi_major_axis"].set(f"{semi_major_axis_km:,.2f} км")

        self._draw_orbits(initial_radius_km, target_radius_km)

    def _validate_radius(self, radius_km: float, field_name: str):
        if radius_km <= EARTH_RADIUS_KM:
            raise ValueError(
                f"{field_name} должен быть больше радиуса Земли ({EARTH_RADIUS_KM:,.0f} км)."
            )

    def _set_empty_results(self):
        for variable in self.result_vars.values():
            variable.set("-")

    def _draw_placeholder(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width() or 620
        height = self.canvas.winfo_height() or 560
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Введите корректные параметры орбит в километрах",
            fill="#d8e5ff",
            font=("Segoe UI", 12, "bold"),
        )

    def _draw_orbits(self, initial_radius_km: float, target_radius_km: float):
        self.canvas.delete("all")
        width = self.canvas.winfo_width() or 620
        height = self.canvas.winfo_height() or 560
        center_x = width / 2 + self.view_offset_x
        center_y = height / 2 + self.view_offset_y

        padding = 52
        max_radius_km = max(initial_radius_km, target_radius_km)
        base_scale = (min(width, height) / 2 - padding) / max_radius_km
        scale = base_scale * self.view_scale

        earth_radius_px = EARTH_RADIUS_KM * scale
        scaled_initial = initial_radius_km * scale
        scaled_target = target_radius_km * scale
        scaled_perigee = min(initial_radius_km, target_radius_km) * scale
        scaled_apogee = max(initial_radius_km, target_radius_km) * scale
        semi_major_px = (scaled_perigee + scaled_apogee) / 2
        focal_offset_px = (scaled_apogee - scaled_perigee) / 2
        semi_minor_px = m.sqrt(max(semi_major_px**2 - focal_offset_px**2, 0))
        transfer_to_outer_orbit = target_radius_km >= initial_radius_km

        self._draw_earth(center_x, center_y, earth_radius_px)
        self._draw_circle(center_x, center_y, scaled_initial, "#57c7ff", 2)
        self._draw_circle(center_x, center_y, scaled_target, "#8de18d", 2)
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
            first_burn_delta_v=self.result_vars["first_burn"].get(),
            second_burn_delta_v=self.result_vars["second_burn"].get(),
            transfer_to_outer_orbit=transfer_to_outer_orbit,
        )

        self.canvas.create_text(
            center_x,
            center_y + earth_radius_px + 16,
            text="Земля",
            fill="#d9e7ff",
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
        steps = 180

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

        self.canvas.create_line(
            *points,
            fill="#ff8c69",
            width=2,
            smooth=True,
        )

    def _draw_burn_markers(
        self,
        center_x: float,
        center_y: float,
        scaled_initial: float,
        scaled_target: float,
        first_burn_delta_v: str,
        second_burn_delta_v: str,
        transfer_to_outer_orbit: bool,
    ):
        if transfer_to_outer_orbit:
            first_point = (center_x - scaled_initial, center_y)
            second_point = (center_x + scaled_target, center_y)
            first_anchor = "ne"
            second_anchor = "sw"
            first_text_offset = (-14, -12)
            second_text_offset = (14, 12)
        else:
            first_point = (center_x + scaled_initial, center_y)
            second_point = (center_x - scaled_target, center_y)
            first_anchor = "nw"
            second_anchor = "se"
            first_text_offset = (14, -12)
            second_text_offset = (-14, 12)

        self._draw_burn_marker(
            x=first_point[0],
            y=first_point[1],
            color="#ffd166",
            title="Первое включение",
            delta_v_text=first_burn_delta_v,
            anchor=first_anchor,
            text_offset=first_text_offset,
        )
        self._draw_burn_marker(
            x=second_point[0],
            y=second_point[1],
            color="#ff9f6e",
            title="Второе включение",
            delta_v_text=second_burn_delta_v,
            anchor=second_anchor,
            text_offset=second_text_offset,
        )

    def _draw_burn_marker(
        self,
        x: float,
        y: float,
        color: str,
        title: str,
        delta_v_text: str,
        anchor: str,
        text_offset: tuple[float, float],
    ):
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
            text=f"{title}\nΔV: {delta_v_text}",
            fill="#fff2cc",
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
                fill="#2f84d6",
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
                r = int(18 + 18 * ocean_mix)
                g = int(74 + 75 * ocean_mix)
                b = int(130 + 85 * ocean_mix)

                land_noise = (
                    m.sin(dx * 7.5)
                    + m.cos(dy * 8.0)
                    + m.sin((dx + dy) * 11.0)
                    + 0.6 * m.cos(m.atan2(dy, dx) * 5.0)
                )

                if land_noise > 1.15:
                    r = int(66 + 45 * (1 - distance))
                    g = int(132 + 65 * (1 - distance))
                    b = int(70 + 30 * (1 - distance))

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

    def _draw_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        color: str,
        width: int,
    ):
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
            ("#57c7ff", "Начальная орбита"),
            ("#8de18d", "Целевая орбита"),
            ("#ff8c69", "Переходная орбита"),
        ]

        x = canvas_width - 205
        y = 26
        for color, text in legend_items:
            self.canvas.create_line(x, y, x + 24, y, fill=color, width=3)
            self.canvas.create_text(
                x + 32,
                y,
                text=text,
                fill="#e4efff",
                anchor="w",
                font=("Segoe UI", 9),
            )
            y += 24


def open_calculation_dialog(master: tk.Misc):
    HohmannTransferDialog(master)


def main():
    root = tk.Tk()
    root.title("Расчет орбитальных маневров")
    root.geometry("440x190")
    root.minsize(440, 190)

    wrapper = ttk.Frame(root, padding=24)
    wrapper.pack(fill="both", expand=True)

    ttk.Label(
        wrapper,
        text="Расчет deltaV для Гомановского перехода",
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w", pady=(0, 8))

    ttk.Label(
        wrapper,
        text=(
            "Откройте всплывающее окно, чтобы ввести радиусы орбит в километрах, "
            "увидеть Землю в масштабе и результаты вычислений."
        ),
        wraplength=380,
        justify="left",
    ).pack(anchor="w", pady=(0, 16))

    ttk.Button(
        wrapper,
        text="Открыть окно расчета",
        command=lambda: open_calculation_dialog(root),
    ).pack(anchor="w")

    open_calculation_dialog(root)
    root.mainloop()


if __name__ == "__main__":
    main()
