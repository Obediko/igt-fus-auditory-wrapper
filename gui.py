from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from igt_fus_auditory.audio import AudioPlayer
from igt_fus_auditory.config import MaskConfig
from igt_fus_auditory.maskfile import load_mask, save_mask
from igt_fus_auditory.session import run_active, run_sham
from igt_fus_auditory.signals import generate_mask


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "study_mask.local.json"
EXAMPLE_CONFIG = ROOT / "config" / "study_mask.example.json"
MASK = ROOT / "masks" / "study_mask.wav"
HOOK = ROOT / "local_fus_hook.py"
LOGS = ROOT / "logs"
GUI_SETTINGS = ROOT / "config" / "gui.local.json"
DEFAULT_ADAPTER = Path(
    r"C:\Users\TUS\FUS-driving-software"
    r"\standalone_driving_system_software\standalone_igt-Obed.py"
)


class AuditoryWrapperGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("IGT FUS Auditory Masking Wrapper")
        self.root.geometry("820x690")
        self.root.minsize(760, 620)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.busy = False
        self.devices: dict[str, int] = {}
        self.device_var = tk.StringVar()
        self.gain_var = tk.StringVar(value="0.02")
        self.calibrated_var = tk.BooleanVar(value=False)
        self.adapter_var = tk.StringVar(value=str(DEFAULT_ADAPTER))
        self.status_var = tk.StringVar(value="Ready for offline setup")

        self._style()
        self._build()
        self._load_gui_settings()
        self._load_config()
        self._refresh_devices()
        self._refresh_summary()

    def _style(self):
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Danger.TButton", foreground="#8b0000")

    def _build(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="IGT FUS Auditory Masking", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Isolated audio wrapper around the locally approved Dortmund delivery hook",
        ).pack(anchor="w", pady=(2, 16))

        settings = ttk.LabelFrame(outer, text="Speaker setup", padding=14)
        settings.pack(fill="x")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Output device").grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.device_box = ttk.Combobox(settings, textvariable=self.device_var, state="readonly")
        self.device_box.grid(row=0, column=1, sticky="ew")
        ttk.Button(settings, text="Refresh", command=self._refresh_devices).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(settings, text="Master gain").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(settings, textvariable=self.gain_var, width=12).grid(row=1, column=1, sticky="w", pady=(12, 0))

        self.calibration_check = ttk.Checkbutton(
            settings,
            text="Speaker output has been measured and approved at the participant position",
            variable=self.calibrated_var,
        )
        self.calibration_check.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        ttk.Label(settings, text="IGT adapter").grid(row=3, column=0, sticky="w", pady=(12, 0), padx=(0, 12))
        ttk.Entry(settings, textvariable=self.adapter_var).grid(row=3, column=1, sticky="ew", pady=(12, 0))
        ttk.Button(settings, text="Browse", command=self._browse_adapter).grid(row=3, column=2, padx=(8, 0), pady=(12, 0))

        controls = ttk.LabelFrame(outer, text="Workflow", padding=14)
        controls.pack(fill="x", pady=(14, 0))
        for column in range(4):
            controls.columnconfigure(column, weight=1)

        self.test_button = ttk.Button(controls, text="1. Test speakers (3 s)", command=self._audio_test)
        self.test_button.grid(row=0, column=0, padx=4, sticky="ew")
        self.save_button = ttk.Button(controls, text="2. Save and freeze mask", command=self._generate)
        self.save_button.grid(row=0, column=1, padx=4, sticky="ew")
        self.sham_button = ttk.Button(controls, text="3. Run sham", command=self._sham)
        self.sham_button.grid(row=0, column=2, padx=4, sticky="ew")
        self.active_button = ttk.Button(
            controls,
            text="4. Run active",
            command=self._active,
            style="Danger.TButton",
        )
        self.active_button.grid(row=0, column=3, padx=4, sticky="ew")

        ttk.Label(
            controls,
            text=(
                "Active calls the local hook. The GUI cannot provide a reliable hardware stop. "
                "Use the laboratory emergency-stop procedure if delivery must be interrupted."
            ),
            wraplength=740,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(12, 0))

        summary_frame = ttk.LabelFrame(outer, text="Current configuration", padding=14)
        summary_frame.pack(fill="x", pady=(14, 0))
        self.summary = tk.Text(summary_frame, height=7, wrap="word", state="disabled", font=("Consolas", 10))
        self.summary.pack(fill="x")

        status_frame = ttk.LabelFrame(outer, text="Status and session output", padding=14)
        status_frame.pack(fill="both", expand=True, pady=(14, 0))
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w")
        self.output = tk.Text(status_frame, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.output.pack(fill="both", expand=True, pady=(8, 0))

    def _load_config(self):
        try:
            path = CONFIG if CONFIG.exists() else EXAMPLE_CONFIG
            config = MaskConfig.from_json(path)
            self.gain_var.set(str(config.master_gain))
            self.calibrated_var.set(bool(config.headphones_calibrated))
            self.saved_device = config.output_device
        except Exception as exc:
            self.saved_device = None
            self._append(f"Configuration load failed: {exc}")

    def _load_gui_settings(self):
        if not GUI_SETTINGS.exists():
            return
        try:
            data = json.loads(GUI_SETTINGS.read_text(encoding="utf-8"))
            if data.get("igt_adapter_path"):
                self.adapter_var.set(str(data["igt_adapter_path"]))
        except Exception as exc:
            self._append(f"GUI settings load failed: {exc}")

    def _save_gui_settings(self):
        GUI_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        GUI_SETTINGS.write_text(
            json.dumps({"igt_adapter_path": self.adapter_var.get().strip()}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _browse_adapter(self):
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Select the local IGT standalone adapter",
            initialdir=str(Path(self.adapter_var.get()).parent),
            filetypes=(("Python files", "*.py"), ("All files", "*.*")),
        )
        if selected:
            self.adapter_var.set(selected)
            self._save_gui_settings()
            self._refresh_summary()

    def _adapter_path(self) -> Path:
        raw = self.adapter_var.get().strip()
        if not raw:
            raise ValueError("Select the local IGT standalone adapter")
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"IGT standalone adapter not found: {path}")
        return path

    def _selected_device(self) -> int:
        label = self.device_var.get()
        if label not in self.devices:
            raise ValueError("Select a valid stereo output device")
        return self.devices[label]

    def _current_config(self) -> MaskConfig:
        base = MaskConfig.from_json(CONFIG if CONFIG.exists() else EXAMPLE_CONFIG)
        gain = float(self.gain_var.get())
        return replace(
            base,
            output_device=self._selected_device(),
            master_gain=gain,
            headphones_calibrated=bool(self.calibrated_var.get()),
        ).validate()

    def _refresh_devices(self):
        try:
            rows = AudioPlayer().list_devices()
            self.devices.clear()
            labels = []
            chosen = None
            for index, device in enumerate(rows):
                if int(device.get("max_output_channels", 0)) < 2:
                    continue
                label = f"{index}: {device.get('name', 'Unknown')}"
                labels.append(label)
                self.devices[label] = index
                if index == self.saved_device:
                    chosen = label
            self.device_box["values"] = labels
            if chosen:
                self.device_var.set(chosen)
            elif labels and not self.device_var.get():
                self.device_var.set(labels[0])
            self._append(f"Found {len(labels)} stereo output device(s).")
        except Exception as exc:
            messagebox.showerror("Audio devices", str(exc))

    def _save_config(self, config: MaskConfig):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        config.to_json(CONFIG)

    def _refresh_summary(self):
        try:
            config = self._current_config()
            lines = [
                f"Protocol: {config.protocol_label}",
                f"Audio: {config.profile}; {config.sample_rate_hz} Hz; device {config.output_device}",
                f"Timing: {config.pre_mask_s:.1f} s pre + {config.stimulation_duration_s:.1f} s window + {config.post_mask_s:.1f} s post",
                f"Mask matching: {config.prf_hz:g} Hz; {config.matched_pulse_width_ms:g} ms; {config.expected_pulses} expected pulses",
                f"Master gain: {config.master_gain:g}; speaker approved: {config.headphones_calibrated}",
                f"Frozen mask: {'present' if MASK.exists() and MASK.with_suffix('.json').exists() else 'not generated'}",
                f"Local FUS hook: {'present' if HOOK.exists() else 'missing'}",
                f"IGT adapter: {self.adapter_var.get().strip() or 'not selected'}",
            ]
        except Exception as exc:
            lines = [f"Configuration incomplete: {exc}"]
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", "\n".join(lines))
        self.summary.configure(state="disabled")

    def _append(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text.rstrip() + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _set_busy(self, busy: bool, status: str):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for button in (self.test_button, self.save_button, self.sham_button, self.active_button):
            button.configure(state=state)
        self.status_var.set(status)

    def _background(self, label: str, work):
        if self.busy:
            return
        self._set_busy(True, label)

        def runner():
            try:
                result = work()
            except BaseException as exc:
                self.root.after(0, lambda: self._finished_error(exc))
            else:
                self.root.after(0, lambda: self._finished_ok(result))

        threading.Thread(target=runner, daemon=True).start()

    def _finished_ok(self, result):
        if result:
            self._append(str(result))
        self._set_busy(False, "Ready")
        self._refresh_summary()

    def _finished_error(self, exc: BaseException):
        self._append(f"ERROR: {type(exc).__name__}: {exc}")
        self._set_busy(False, "Operation failed")
        messagebox.showerror("Operation failed", f"{type(exc).__name__}: {exc}")

    def _audio_test(self):
        def work():
            config = replace(
                self._current_config(),
                stimulation_duration_s=3.0,
                pre_mask_s=0.0,
                post_mask_s=0.0,
                headphones_calibrated=True,
            )
            generated = generate_mask(config)
            player = AudioPlayer(config.output_device)
            device = player.verify(config.sample_rate_hz)
            player.play(generated.audio, generated.sample_rate_hz)
            player.wait()
            return f"Speaker test complete: {device.get('name', config.output_device)}"

        self._background("Playing three-second speaker test", work)

    def _generate(self):
        try:
            config = self._current_config()
            if not config.headphones_calibrated:
                raise ValueError("Speaker output must be measured and approved before freezing the study mask")
            self._save_config(config)
        except Exception as exc:
            messagebox.showerror("Cannot freeze mask", str(exc))
            return

        def work():
            generated = generate_mask(config)
            wav, sidecar = save_mask(generated, MASK)
            return f"Frozen mask saved and hashed:\n{wav}\n{sidecar}"

        self._background("Generating and hashing final mask", work)

    def _require_ready_mask(self):
        config = self._current_config()
        if not config.headphones_calibrated:
            raise ValueError("Speaker output is not marked measured and approved")
        if not MASK.exists() or not MASK.with_suffix(".json").exists():
            raise FileNotFoundError("Generate the frozen mask before running a session")
        frozen = load_mask(MASK)
        if frozen.config.to_dict() != config.to_dict():
            raise ValueError("Current settings differ from the frozen mask; generate it again")
        return frozen

    def _sham(self):
        try:
            mask = self._require_ready_mask()
        except Exception as exc:
            messagebox.showerror("Sham unavailable", str(exc))
            return
        log = LOGS / "sham_session.jsonl"
        self._background("Running sham session", lambda: (run_sham(mask, log), f"Sham complete. Log: {log}")[1])

    def _active(self):
        try:
            mask = self._require_ready_mask()
            if not HOOK.exists():
                raise FileNotFoundError(f"Local FUS hook not found: {HOOK}")
            adapter = self._adapter_path()
            self._save_gui_settings()
        except Exception as exc:
            messagebox.showerror("Active unavailable", str(exc))
            return

        warning = (
            "ACTIVE DELIVERY REQUEST\n\n"
            "This will call the local Dortmund FUS hook after the pre-mask interval. "
            "The GUI cannot reliably stop a sequence after dispatch. Confirm the approved setup, "
            "coupling, monitoring and hardware emergency stop before continuing.\n\n"
            "Type EXECUTE ACTIVE to continue."
        )
        response = simpledialog.askstring("Confirm active delivery", warning, parent=self.root)
        if response != "EXECUTE ACTIVE":
            self._append("Active request cancelled before FUS preparation.")
            return

        log = LOGS / "active_session.jsonl"
        os.environ["IGT_FUS_ADAPTER_PATH"] = str(adapter)
        self._background(
            "Active session running; use the hardware emergency stop if interruption is required",
            lambda: (run_active(mask, HOOK, allow_active=True, log_path=log), f"Active complete. Log: {log}")[1],
        )

    def _close(self):
        if self.busy:
            messagebox.showwarning(
                "Operation running",
                "Do not close the interface during a session. Closing it is not a hardware emergency stop.",
            )
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    AuditoryWrapperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
