from __future__ import annotations

import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from igt_fus_auditory.audio import AudioPlayer
from igt_fus_auditory.config import MaskConfig
from igt_fus_auditory.maskfile import save_mask
from igt_fus_auditory.session import run_active, run_sham
from igt_fus_auditory.signals import generate_mask


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "study_mask.local.json"
EXAMPLE = ROOT / "config" / "study_mask.example.json"
GUI_SETTINGS = ROOT / "config" / "gui.local.json"
MASK = ROOT / "masks" / "study_mask.wav"
HOOK = ROOT / "local_fus_hook.py"
LOGS = ROOT / "logs"
DEFAULT_ADAPTER = Path(r"C:\Users\TUS\FUS-driving-software\standalone_driving_system_software\standalone_igt-Obed.py")
PLAYBACK_MODES = ("Matching Only", "Background Only", "Combined")
BACKGROUND_PROFILES = {
    "White Noise": "matched_plus_white",
    "Pink Noise": "matched_plus_pink",
    "Narrowband Noise": "matched_plus_narrowband",
    "Auditory Mondrian": "auditory_mondrian",
}
PROFILE_BACKGROUNDS = {value: key for key, value in BACKGROUND_PROFILES.items()}
PROFILE_BACKGROUNDS["simple_prf"] = "White Noise"


class App:
    FLOAT_FIELDS = (
        "stimulation_duration_s", "prf_hz", "matched_pulse_width_ms", "pre_mask_s", "post_mask_s",
        "carrier_hz", "matching_gain", "background_gain", "master_gain", "audio_ramp_ms", "stereo_pan",
    )

    def __init__(self, root):
        self.root = root
        root.title("Dortmund IGT D054 | TUS Auditory Masking")
        root.geometry("1040x850")
        root.minsize(940, 740)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.vars = {}
        self.devices = {}
        self.player = None
        self.busy = False
        self.calibrated = tk.BooleanVar(master=root, value=False)
        self.condition = tk.StringVar(value="sham")
        self.playback_mode = tk.StringVar(value="Combined")
        self.background_type = tk.StringVar(value="White Noise")
        self.adapter = tk.StringVar(value=str(DEFAULT_ADAPTER))
        self.ultrasound_khz = tk.StringVar(value="300")
        self.status_var = tk.StringVar(value="Ready")
        self._build()
        self._load()
        self.refresh_devices()
        self.show_delivery()

    def field(self, frame, row, col, label, name):
        ttk.Label(frame, text=label).grid(row=row, column=col * 2, sticky="w", padx=(8, 4), pady=4)
        self.vars[name] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars[name], width=17).grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 10), pady=4)

    def combo(self, frame, row, col, label, name, values):
        ttk.Label(frame, text=label).grid(row=row, column=col * 2, sticky="w", padx=(8, 4), pady=4)
        self.vars[name] = tk.StringVar()
        ttk.Combobox(frame, textvariable=self.vars[name], values=values, state="readonly", width=21).grid(row=row, column=col * 2 + 1, sticky="ew", padx=(0, 10), pady=4)

    def _build(self):
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scroll = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        box = ttk.Frame(canvas, padding=15)
        win = canvas.create_window((0, 0), window=box, anchor="nw")
        box.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

        ttk.Label(box, text="IGT D054 / pmEC auditory masking", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(box, text="Research use only. Identical frozen audio is required for active and sham.").pack(anchor="w", pady=(2, 9))

        protocol = ttk.LabelFrame(box, text="Ultrasound-matched timing", padding=5)
        protocol.pack(fill="x", pady=4)
        for i in range(4): protocol.columnconfigure(i, weight=1)
        self.field(protocol, 0, 0, "PRF (Hz)", "prf_hz")
        self.field(protocol, 0, 1, "Pulse duration (ms)", "matched_pulse_width_ms")
        self.field(protocol, 1, 0, "Sonication (s)", "stimulation_duration_s")
        ttk.Label(protocol, text="Ultrasound carrier (kHz)").grid(row=1, column=2, sticky="w", padx=(8, 4), pady=4)
        ttk.Entry(protocol, textvariable=self.ultrasound_khz, width=17).grid(row=1, column=3, sticky="ew", padx=(0, 10), pady=4)
        self.field(protocol, 2, 0, "Pre-mask (s)", "pre_mask_s")
        self.field(protocol, 2, 1, "Post-mask (s)", "post_mask_s")

        sound = ttk.LabelFrame(box, text="Auditory matching and background", padding=5)
        sound.pack(fill="x", pady=4)
        for i in range(4): sound.columnconfigure(i, weight=1)
        self.field(sound, 0, 0, "Audible carrier (Hz)", "carrier_hz")
        self.field(sound, 0, 1, "Sample rate (Hz)", "sample_rate_hz")
        ttk.Label(sound, text="Playback mode").grid(row=1, column=0, sticky="w", padx=(8, 4), pady=4)
        ttk.Combobox(sound, textvariable=self.playback_mode, values=PLAYBACK_MODES, state="readonly", width=21).grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)
        ttk.Label(sound, text="Background").grid(row=1, column=2, sticky="w", padx=(8, 4), pady=4)
        ttk.Combobox(sound, textvariable=self.background_type, values=tuple(BACKGROUND_PROFILES), state="readonly", width=21).grid(row=1, column=3, sticky="ew", padx=(0, 10), pady=4)
        self.field(sound, 2, 0, "Matching gain (0–1)", "matching_gain")
        self.field(sound, 2, 1, "Background gain (0–1)", "background_gain")
        self.field(sound, 3, 0, "Master gain (0–1)", "master_gain")
        self.field(sound, 3, 1, "Stereo pan (-1 to 1)", "stereo_pan")
        self.field(sound, 4, 0, "Pulse ramp (ms)", "audio_ramp_ms")
        self.field(sound, 4, 1, "Frozen random seed", "random_seed")
        ttk.Label(
            sound,
            text=("Study preset: Combined playback with White Noise. Matching and background gains set the mix; "
                  "Master gain controls digital output and must follow the approved speaker measurement."),
            foreground="#365a7c",
            wraplength=760,
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(5, 7))
        ttk.Button(sound, text="Load study audio defaults", command=self.load_audio_defaults).grid(row=5, column=3, sticky="e", padx=(0, 10), pady=(5, 7))

        setup = ttk.LabelFrame(box, text="Speaker setup, local delivery path and allocation", padding=6)
        setup.pack(fill="x", pady=4)
        setup.columnconfigure(1, weight=1)
        ttk.Label(setup, text="Speaker").grid(row=0, column=0, sticky="w", padx=(8, 4), pady=4)
        self.device = tk.StringVar()
        self.device_box = ttk.Combobox(setup, textvariable=self.device, state="readonly")
        self.device_box.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=4)
        ttk.Button(setup, text="Refresh", command=self.refresh_devices).grid(row=0, column=2, padx=(0, 8))
        ttk.Label(setup, text="IGT standalone").grid(row=1, column=0, sticky="w", padx=(8, 4), pady=4)
        ttk.Entry(setup, textvariable=self.adapter).grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=4)
        ttk.Button(setup, text="Browse", command=self.browse).grid(row=1, column=2, padx=(0, 8))
        ttk.Label(setup, text="Condition").grid(row=2, column=0, sticky="w", padx=(8, 4), pady=4)
        ttk.Combobox(setup, textvariable=self.condition, values=("sham", "active"), state="readonly", width=12).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Checkbutton(setup, text="Speaker output has been measured and approved at the participant position", variable=self.calibrated).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=5)
        ttk.Label(setup, text="The visible condition selector is for setup. Blinded allocation must be controlled separately.", foreground="#7a4200").grid(row=4, column=0, columnspan=3, sticky="w", padx=8)

        self.delivery = tk.Text(box, height=5, state="disabled", font=("Consolas", 9))
        self.delivery.pack(fill="x", pady=4)
        controls = ttk.Frame(box)
        controls.pack(fill="x", pady=7)
        self.buttons = []
        for label, fn in (("Generate", self.generate), ("Test speakers (3 s)", self.test_speakers), ("Play full preview", self.preview), ("Stop audio", self.stop_preview), ("Save WAV as…", self.export), ("Save settings", self.save_settings)):
            b = ttk.Button(controls, text=label, command=fn); b.pack(side="left", padx=3); self.buttons.append(b)
        b = ttk.Button(controls, text="Run selected session", command=self.run_session); b.pack(side="right", padx=3); self.buttons.append(b)
        ttk.Label(box, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.log = tk.Text(box, height=11, state="disabled", wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.message(f"Configuration: {CONFIG}")
        self.message("Default condition is sham. Sham never calls the local FUS hook.")

    def _load(self):
        gui_data = {}
        if GUI_SETTINGS.exists():
            try: gui_data = json.loads(GUI_SETTINGS.read_text(encoding="utf-8"))
            except Exception as exc: self.message(f"GUI settings warning: {exc}")
        if gui_data.get("igt_adapter_path"): self.adapter.set(gui_data["igt_adapter_path"])
        cfg = MaskConfig.from_json(CONFIG if CONFIG.exists() else EXAMPLE)
        data = cfg.to_dict()
        for name, var in self.vars.items(): var.set(str(data[name]))
        self.playback_mode.set(gui_data.get("playback_mode", "Combined"))
        self.background_type.set(gui_data.get("background_type", PROFILE_BACKGROUNDS.get(cfg.profile, "White Noise")))
        if "matching_gain_setting" in gui_data: self.vars["matching_gain"].set(str(gui_data["matching_gain_setting"]))
        if "background_gain_setting" in gui_data: self.vars["background_gain"].set(str(gui_data["background_gain_setting"]))
        self.calibrated.set(cfg.headphones_calibrated)
        self.saved_device = cfg.output_device

    def collect(self):
        data = MaskConfig.from_json(CONFIG if CONFIG.exists() else EXAMPLE).to_dict()
        for name in self.FLOAT_FIELDS: data[name] = float(self.vars[name].get().strip())
        data["sample_rate_hz"] = int(self.vars["sample_rate_hz"].get().strip())
        data["random_seed"] = int(self.vars["random_seed"].get().strip())
        data["profile"] = BACKGROUND_PROFILES[self.background_type.get()]
        if self.playback_mode.get() == "Matching Only": data["background_gain"] = 0.0
        elif self.playback_mode.get() == "Background Only": data["matching_gain"] = 0.0
        data["output_device"] = self.selected_device()
        data["headphones_calibrated"] = bool(self.calibrated.get())
        return MaskConfig(**data).validate()

    def load_audio_defaults(self):
        self.playback_mode.set("Combined")
        self.background_type.set("White Noise")
        defaults = {
            "carrier_hz": "14000.0",
            "sample_rate_hz": "48000",
            "matching_gain": "0.35",
            "background_gain": "0.30",
            "audio_ramp_ms": "5.0",
            "stereo_pan": "0.0",
            "random_seed": "20260903",
        }
        for name, value in defaults.items(): self.vars[name].set(value)
        self.message("Loaded the agreed study audio defaults. Master gain was left unchanged because it is calibration-dependent.")

    def selected_device(self):
        if self.device.get() not in self.devices: raise ValueError("Select a valid stereo speaker/output")
        return self.devices[self.device.get()]

    def refresh_devices(self):
        try:
            self.devices = {f"{i}: {d.get('name', 'Unknown')}": i for i, d in enumerate(AudioPlayer().list_devices()) if int(d.get("max_output_channels", 0)) >= 2}
            values = list(self.devices); self.device_box["values"] = values
            selected = next((x for x, i in self.devices.items() if i == getattr(self, "saved_device", None)), None)
            self.device.set(selected or (values[0] if values else "")); self.message(f"Found {len(values)} stereo output device(s).")
        except Exception as exc: self.error(exc)

    def browse(self):
        p = filedialog.askopenfilename(title="Select local IGT standalone adapter", initialdir=str(Path(self.adapter.get()).parent), filetypes=(("Python", "*.py"),))
        if p: self.adapter.set(p); self.save_gui(); self.show_delivery()

    def adapter_path(self):
        p = Path(self.adapter.get().strip()).resolve()
        if not p.is_file(): raise FileNotFoundError(f"IGT standalone adapter not found: {p}")
        return p

    def adapter_values(self):
        tree = ast.parse(self.adapter_path().read_text(encoding="utf-8-sig"))
        wanted = {"driving_sys", "transducer", "oper_freq", "focus_wrt_mid_bowl", "press", "pulse_dur", "pulse_rep_int", "pulse_ramp_shape", "pulse_ramp_dur", "pulse_train_rep_dur"}
        out = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute):
                t = node.targets[0]
                if isinstance(t.value, ast.Name) and t.value.id == "seq1" and t.attr in wanted:
                    try: out[t.attr] = ast.literal_eval(node.value)
                    except (ValueError, TypeError): pass
        return out

    def show_delivery(self):
        try:
            p = self.adapter_values(); lines = [f"IGT adapter: {self.adapter_path()}", f"Delivery: {p.get('driving_sys')} | {p.get('transducer')} | one transducer", f"FUS: {p.get('oper_freq')} kHz | {p.get('press')} MPa free-water | {p.get('focus_wrt_mid_bowl')} mm focus", f"Timing: {p.get('pulse_dur')} ms pulse | {p.get('pulse_rep_int')} ms interval | {p.get('pulse_train_rep_dur')} s"]
        except Exception as exc: lines = [f"IGT adapter unavailable: {exc}"]
        self.delivery.configure(state="normal"); self.delivery.delete("1.0", "end"); self.delivery.insert("1.0", "\n".join(lines)); self.delivery.configure(state="disabled")

    def check_match(self, cfg):
        p = self.adapter_values(); pairs = (("PRF", cfg.prf_hz, 1000 / float(p["pulse_rep_int"])), ("pulse duration", cfg.matched_pulse_width_ms, float(p["pulse_dur"])), ("duration", cfg.stimulation_duration_s, float(p["pulse_train_rep_dur"])), ("carrier", float(self.ultrasound_khz.get()), float(p["oper_freq"])))
        bad = [f"{n}: interface {a:g}, IGT {b:g}" for n, a, b in pairs if abs(a-b) > 1e-9]
        if bad: raise ValueError("Auditory timing does not match the IGT adapter:\n" + "\n".join(bad))

    def message(self, text):
        self.log.configure(state="normal"); self.log.insert("end", str(text).rstrip()+"\n"); self.log.see("end"); self.log.configure(state="disabled")

    def error(self, exc): self.message(f"ERROR: {exc}"); messagebox.showerror("Auditory masking", str(exc))

    def generate(self):
        try:
            cfg = self.collect(); self.check_match(cfg); self.generated = generate_mask(cfg); self.message(f"Generated {self.generated.duration_s:.2f} s stereo mask, {cfg.expected_pulses} pulses, peak {self.generated.peak:.3f}."); return self.generated
        except Exception as exc: self.error(exc)

    def preview(self):
        g = self.generate()
        if not g: return
        try:
            self.stop_preview(True); self.player = AudioPlayer(g.config.output_device); d = self.player.verify(g.sample_rate_hz); self.player.play(g.audio, g.sample_rate_hz); self.message(f"Preview playing through {d.get('name')}.")
        except Exception as exc: self.error(exc)

    def test_speakers(self):
        try:
            cfg = self.collect()
            test_cfg = replace(cfg, stimulation_duration_s=3.0, pre_mask_s=0.0, post_mask_s=0.0)
            g = generate_mask(test_cfg)
            self.stop_preview(True)
            self.player = AudioPlayer(g.config.output_device)
            d = self.player.verify(g.sample_rate_hz)
            self.player.play(g.audio, g.sample_rate_hz)
            self.message(f"Three-second speaker test playing through {d.get('name')}. No FUS connection or delivery is made.")
        except Exception as exc: self.error(exc)

    def stop_preview(self, quiet=False):
        if self.player: self.player.stop(); self.player = None
        if not quiet: self.message("Audio preview stopped.")

    def save_gui(self):
        settings = {
            "igt_adapter_path": self.adapter.get().strip(),
            "playback_mode": self.playback_mode.get(),
            "background_type": self.background_type.get(),
            "matching_gain_setting": float(self.vars["matching_gain"].get()),
            "background_gain_setting": float(self.vars["background_gain"].get()),
        }
        GUI_SETTINGS.parent.mkdir(parents=True, exist_ok=True); GUI_SETTINGS.write_text(json.dumps(settings, indent=2)+"\n", encoding="utf-8")

    def save_settings(self):
        try:
            cfg = self.collect(); self.check_match(cfg); cfg.to_json(CONFIG); self.save_gui(); self.saved_device = cfg.output_device; self.show_delivery(); self.message(f"Saved settings: {CONFIG}"); return cfg
        except Exception as exc: self.error(exc)

    def export(self):
        g = self.generate()
        if not g: return
        p = filedialog.asksaveasfilename(defaultextension=".wav", initialfile="pmEC_5Hz_20ms_90s_frozen_mask.wav", filetypes=(("WAV", "*.wav"),))
        if p:
            wav, meta = save_mask(g, p); self.message(f"Saved WAV: {wav}\nSaved metadata: {meta}")

    def background(self, label, fn):
        if self.busy: return
        self.busy=True; self.status_var.set(label)
        for b in self.buttons: b.configure(state="disabled")
        def work():
            try: result=fn(); self.root.after(0, lambda: self.finish(result, None))
            except BaseException as exc: self.root.after(0, lambda: self.finish(None, exc))
        threading.Thread(target=work, daemon=True).start()

    def finish(self, result, exc):
        self.busy=False; self.status_var.set("Ready" if not exc else "Failed")
        for b in self.buttons: b.configure(state="normal")
        if exc: self.error(exc)
        elif result: self.message(result)

    def run_session(self):
        cfg = self.save_settings()
        if not cfg: return
        try:
            if not cfg.headphones_calibrated: raise RuntimeError("Confirm measured and approved speaker output first")
            self.check_match(cfg); g=generate_mask(cfg); MASK.parent.mkdir(parents=True, exist_ok=True); save_mask(g, MASK); LOGS.mkdir(parents=True, exist_ok=True); self.stop_preview(True)
            if self.condition.get()=="sham": self.background("Sham running", lambda: (run_sham(g, LOGS/"sham_session.jsonl"), "Sham complete")[1]); return
            if not HOOK.exists(): raise FileNotFoundError(f"Local hook not found: {HOOK}")
            answer=simpledialog.askstring("Confirm active delivery", "Confirm coupling, targeting, exposure, monitoring and hardware emergency stop.\n\nType EXECUTE ACTIVE to continue.")
            if answer!="EXECUTE ACTIVE": self.message("Active cancelled before preparation."); return
            os.environ["IGT_FUS_ADAPTER_PATH"]=str(self.adapter_path()); self.background("Active running; use hardware emergency stop if required", lambda: (run_active(g, HOOK, allow_active=True, log_path=LOGS/"active_session.jsonl"), "Active complete")[1])
        except Exception as exc: self.error(exc)

    def close(self):
        if self.busy: messagebox.showwarning("Session running", "Do not close during a session. Closing is not a hardware emergency stop."); return
        self.stop_preview(True); self.root.destroy()


def main():
    root=tk.Tk(); App(root); root.mainloop()


if __name__=="__main__": main()
