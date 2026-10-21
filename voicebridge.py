import argparse
import ctypes
import json
import os
import queue
import shutil
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import PySide6

PYSIDE_DIR = os.path.dirname(PySide6.__file__)
try:
    os.add_dll_directory(PYSIDE_DIR)
except Exception:
    pass
os.environ["PATH"] = PYSIDE_DIR + os.pathsep + os.environ.get("PATH", "")

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import backend
import cn2kana
from backend import (
    APP_DIR,
    DEFAULT_CONFIG,
    DEFAULT_EDGE_VOICE,
    Device,
    EDGE_ENGINE,
    EDGE_VOICES,
    EdgeTTS,
    Hotkey,
    KOKORO_ENGINE,
    KOKORO_MODEL,
    KOKORO_VOICES,
    KOKORO_VOICES_FILE,
    KokoroTTS,
    LOCAL_APP_DIR,
    OLD_APP_DIR,
    OLD_LOCAL_APP_DIR,
    PIPER_DIR,
    PIPER_ENGINE,
    PIPER_EXE,
    PIPER_MODELS_DIR,
    PiperTTS,
    VOICEVOX_ENGINE,
    Voicevox,
    VoicevoxManager,
    CONFIG_PATH,
    default_output_device,
    find_device_by_hint,
    flatten_speakers,
    list_output_devices,
    load_config,
    osc_send,
    parse_wav,
    play_audio,
    save_config,
)
from pythonosc.udp_client import SimpleUDPClient

APP_NAME = "VoiceBridge"
VOICEVOX_CN_ENGINE = "VOICEVOX 中文 (cn2kana)"
VOICEVOX_CN_KEY = "voicevox_cn"
VOICEVOX_KEYS = ("voicevox", VOICEVOX_CN_KEY)
EDGE_ANIME_ENGINE = "Edge TTS Anime"
EDGE_ANIME_KEY = "edge_anime"
EDGE_ANIME_PITCH_HZ = 50
ENGINE_ORDER = [
    VOICEVOX_ENGINE,
    VOICEVOX_CN_ENGINE,
    EDGE_ENGINE,
    EDGE_ANIME_ENGINE,
    PIPER_ENGINE,
    KOKORO_ENGINE,
]
ENGINE_KEYS = ["voicevox", "voicevox_cn", "edge", "edge_anime", "piper", "kokoro"]
COMPACT_HEIGHT = 180
EXPANDED_HEIGHT = 434
WINDOW_WIDTH = 680


def data_paths():
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "ui" / "VoiceBridge.qml"
    return Path(__file__).resolve().parent / "ui" / "VoiceBridge.qml"


def migrate_old_data():
    if CONFIG_PATH.exists():
        return
    old_config = OLD_APP_DIR / "config.json"
    if not old_config.exists():
        return

    for name, target in (("piper", PIPER_DIR), ("kokoro", backend.KOKORO_DIR)):
        old = OLD_LOCAL_APP_DIR / name
        if old.exists() and not target.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(target))
            except Exception:
                try:
                    shutil.copytree(old, target)
                except Exception:
                    pass

    try:
        data = json.loads(old_config.read_text(encoding="utf-8"))
    except Exception:
        return

    def rewrite(value):
        if not value:
            return value
        try:
            path = Path(str(value))
            relative = path.relative_to(OLD_LOCAL_APP_DIR)
            return str(LOCAL_APP_DIR / relative)
        except Exception:
            return value

    for key in (
        "piper_exe",
        "piper_models_dir",
        "piper_model",
        "kokoro_model",
        "kokoro_voices",
        "voicevox_engine_exe",
    ):
        if key in data:
            data[key] = rewrite(data[key])

    data.setdefault("window_alpha", 0.70)
    data.setdefault("settings_expanded", False)
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


class AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


class BridgeApp(QObject):
    enginesChanged = Signal()
    engineIndexChanged = Signal()
    voicesChanged = Signal()
    voiceIndexChanged = Signal()
    currentVoiceChanged = Signal()
    outputsChanged = Signal()
    outputIndexChanged = Signal()
    monitorIndexChanged = Signal()
    speedChanged = Signal()
    windowAlphaChanged = Signal()
    flagsChanged = Signal()
    expandedChanged = Signal()
    statusChanged = Signal()
    focusInput = Signal()
    toggleWindowSignal = Signal()
    logSignal = Signal(str)
    doneSignal = Signal(str)
    errorSignal = Signal(str)
    voicesSignal = Signal(object)
    voicesErrorSignal = Signal(str)

    def __init__(self, config: dict, config_path: Path, start_hidden: bool = False):
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.start_hidden = start_hidden
        self.window = None
        self.jobs: queue.Queue = queue.Queue()
        self.devices: list[Device] = []
        self._outputs: list[str] = []
        self._output_index = -1
        self._monitor_index = -1
        self._output_enabled = bool(config.get("output_enabled", True))
        self._voices: list[str] = []
        self._voice_index = -1
        self._current_voice = ""
        self._speaker_map: dict[str, int] = {}
        self._edge_map: dict[str, str] = {}
        self._piper_map: dict[str, str] = {}
        self._kokoro_map: dict[str, str] = {}
        self._engine_index = ENGINE_KEYS.index(
            str(config.get("tts_engine", "voicevox")).lower()
        ) if str(config.get("tts_engine", "voicevox")).lower() in ENGINE_KEYS else 0
        self._engine_key = ENGINE_KEYS[self._engine_index]
        self._speed = max(0.5, min(2.0, float(config.get("speed_scale", 1.0))))
        self._window_alpha = max(0.25, min(1.0, float(config.get("window_alpha", 0.70))))
        self._chatbox = bool(config.get("send_chatbox", True))
        self._typing = bool(config.get("send_typing", True))
        self._monitor = bool(config.get("monitor", False))
        self._hide_after_send = bool(config.get("hide_after_send", False))
        self._expanded = bool(config.get("settings_expanded", False))
        self._status_text = "启动中..."
        self._status_kind = "starting"
        self._typing_sent = False
        self._busy = False
        self._device_explicit = False
        self._monitor_device_explicit = False
        self._window_x = config.get("window_x")
        self._window_y = config.get("window_y")

        self.osc = SimpleUDPClient(
            str(config.get("osc_host", "127.0.0.1")),
            int(config.get("osc_port", 9000)),
        )
        self.voicevox = Voicevox(
            str(config.get("voicevox_url", DEFAULT_CONFIG["voicevox_url"]))
        )
        self.voicevox_manager = VoicevoxManager(
            self.voicevox,
            str(config.get("voicevox_engine_exe", "") or ""),
        )
        self.edge = EdgeTTS(str(config.get("edge_proxy", "")))
        self.piper = PiperTTS(
            str(config.get("piper_exe", PIPER_EXE)),
            str(config.get("piper_models_dir", PIPER_MODELS_DIR)),
        )
        self.kokoro = KokoroTTS(
            str(config.get("kokoro_model", KOKORO_MODEL)),
            str(config.get("kokoro_voices", KOKORO_VOICES_FILE)),
        )

        self._connect_signals()
        threading.Thread(target=self.worker_loop, daemon=True).start()
        self._start_hotkeys()
        self.refresh_devices()
        self.refresh_voices()

    def _connect_signals(self):
        self.logSignal.connect(self._on_log, Qt.QueuedConnection)
        self.doneSignal.connect(self._on_done, Qt.QueuedConnection)
        self.errorSignal.connect(self._on_error, Qt.QueuedConnection)
        self.voicesSignal.connect(self._on_voices, Qt.QueuedConnection)
        self.voicesErrorSignal.connect(self._on_voices_error, Qt.QueuedConnection)
        self.toggleWindowSignal.connect(self.toggle_window, Qt.QueuedConnection)

    def _start_hotkeys(self):
        self.show_hotkey = Hotkey(
            lambda: self.toggleWindowSignal.emit(),
            hotkey_id=1,
        )
        self.show_hotkey.start()
        self.show_hotkey.ok.wait(1.0)
        if self.show_hotkey.failed:
            self._set_status("窗口热键注册失败，可能被其它程序占用", "error")
        elif self._status_kind != "error":
            self._set_status("就绪 — Ctrl+Alt+T 显示/隐藏", "ready")

    def _get_engines(self):
        return ENGINE_ORDER

    engines = Property("QVariantList", _get_engines, constant=True)

    def _get_engine_index(self):
        return self._engine_index

    def _set_engine_index(self, value):
        value = max(0, min(len(ENGINE_ORDER) - 1, int(value)))
        if value == self._engine_index:
            return
        self._engine_index = value
        self.engineIndexChanged.emit()
        self._on_engine_changed()

    engineIndex = Property(
        int,
        _get_engine_index,
        _set_engine_index,
        notify=engineIndexChanged,
    )

    def _get_voices(self):
        return self._voices

    voices = Property("QVariantList", _get_voices, notify=voicesChanged)

    def _get_voice_index(self):
        return self._voice_index

    def _set_voice_index(self, value):
        if not self._voices:
            return
        value = max(0, min(len(self._voices) - 1, int(value)))
        if value == self._voice_index:
            return
        self._voice_index = value
        self._current_voice = self._voices[value]
        self.voiceIndexChanged.emit()
        self.currentVoiceChanged.emit()
        self._remember_voice()

    voiceIndex = Property(
        int,
        _get_voice_index,
        _set_voice_index,
        notify=voiceIndexChanged,
    )

    def _get_current_voice(self):
        return self._current_voice

    currentVoice = Property(
        str,
        _get_current_voice,
        notify=currentVoiceChanged,
    )

    def _get_outputs(self):
        return self._outputs

    outputs = Property("QVariantList", _get_outputs, notify=outputsChanged)

    def _get_output_index(self):
        return self._output_index

    def _set_output_index(self, value):
        if not self._outputs:
            return
        value = max(0, min(len(self._outputs) - 1, int(value)))
        if value == self._output_index:
            return
        self._output_index = value
        self._device_explicit = True
        self.config["output_device"] = self.devices[value].name
        self.outputIndexChanged.emit()
        self._persist()

    outputIndex = Property(
        int,
        _get_output_index,
        _set_output_index,
        notify=outputIndexChanged,
    )

    def _get_output_enabled(self):
        return self._output_enabled

    def _set_output_enabled(self, value):
        value = bool(value)
        if value == self._output_enabled:
            return
        self._output_enabled = value
        self.flagsChanged.emit()
        self._persist()

    outputEnabled = Property(
        bool,
        _get_output_enabled,
        _set_output_enabled,
        notify=flagsChanged,
    )

    def _get_monitor_index(self):
        return self._monitor_index

    def _set_monitor_index(self, value):
        if not self._outputs:
            return
        value = max(0, min(len(self._outputs) - 1, int(value)))
        if value == self._monitor_index:
            return
        self._monitor_index = value
        self._monitor_device_explicit = True
        self.config["monitor_device"] = self.devices[value].name
        self.monitorIndexChanged.emit()
        self._persist()

    monitorIndex = Property(
        int,
        _get_monitor_index,
        _set_monitor_index,
        notify=monitorIndexChanged,
    )

    def _get_speed(self):
        return self._speed

    def _set_speed(self, value):
        value = max(0.5, min(2.0, float(value)))
        if abs(value - self._speed) < 0.0001:
            return
        self._speed = value
        self.config["speed_scale"] = value
        self.speedChanged.emit()
        self._persist()

    speed = Property(float, _get_speed, _set_speed, notify=speedChanged)

    def _get_window_alpha(self):
        return self._window_alpha

    def _set_window_alpha(self, value):
        value = max(0.25, min(1.0, float(value)))
        if abs(value - self._window_alpha) < 0.0001:
            return
        self._window_alpha = value
        self.config["window_alpha"] = value
        self.windowAlphaChanged.emit()
        self._persist()

    windowAlpha = Property(
        float,
        _get_window_alpha,
        _set_window_alpha,
        notify=windowAlphaChanged,
    )

    def _get_chatbox(self):
        return self._chatbox

    def _set_chatbox(self, value):
        self._chatbox = bool(value)
        self.flagsChanged.emit()
        self._persist()

    chatbox = Property(bool, _get_chatbox, _set_chatbox, notify=flagsChanged)

    def _get_typing(self):
        return self._typing

    def _set_typing(self, value):
        self._typing = bool(value)
        if not self._typing and self._typing_sent:
            self._send_typing(False)
        self.flagsChanged.emit()
        self._persist()

    typing = Property(bool, _get_typing, _set_typing, notify=flagsChanged)

    def _get_monitor(self):
        return self._monitor

    def _set_monitor(self, value):
        self._monitor = bool(value)
        self.flagsChanged.emit()
        self._persist()

    monitor = Property(bool, _get_monitor, _set_monitor, notify=flagsChanged)

    def _get_hide_after_send(self):
        return self._hide_after_send

    def _set_hide_after_send(self, value):
        self._hide_after_send = bool(value)
        self.flagsChanged.emit()
        self._persist()

    hideAfterSend = Property(
        bool,
        _get_hide_after_send,
        _set_hide_after_send,
        notify=flagsChanged,
    )

    def _get_expanded(self):
        return self._expanded

    def _set_expanded(self, value):
        value = bool(value)
        if value == self._expanded:
            return
        self._expanded = value
        self.config["settings_expanded"] = value
        self.expandedChanged.emit()
        QTimer.singleShot(0, self._clamp_position)
        self._persist()

    expanded = Property(
        bool,
        _get_expanded,
        _set_expanded,
        notify=expandedChanged,
    )

    def _get_status_text(self):
        return self._status_text

    statusText = Property(
        str,
        _get_status_text,
        notify=statusChanged,
    )

    def _get_status_kind(self):
        return self._status_kind

    statusKind = Property(
        str,
        _get_status_kind,
        notify=statusChanged,
    )

    def _get_max_chars(self):
        return int(self.config.get("max_chars", 144))

    maxChars = Property(int, _get_max_chars, constant=True)

    def _set_status(self, text: str, kind: str = "") -> None:
        if not kind:
            kind = self._kind_for(text)
        self._status_text = text
        self._status_kind = kind
        self.statusChanged.emit()

    @staticmethod
    def _kind_for(text: str) -> str:
        if any(value in text for value in ("错误", "失败", "未连接", "不存在")):
            return "error"
        if any(value in text for value in ("启动", "合成", "播放", "停止", "加载")):
            return "starting"
        return "ready"

    def _on_log(self, text: str) -> None:
        self._set_status(text)

    def _on_done(self, text: str) -> None:
        self._busy = False
        self._set_status(f"完成: {text[:48]}", "ready")

    def _on_error(self, text: str) -> None:
        self._busy = False
        self._set_status(f"错误: {text}", "error")

    def current_engine(self) -> str:
        return ENGINE_KEYS[self._engine_index]

    def _on_engine_changed(self) -> None:
        previous = self._engine_key
        engine = self.current_engine()
        self._engine_key = engine
        self.config["tts_engine"] = engine
        self._speaker_map.clear()
        self._edge_map.clear()
        self._piper_map.clear()
        self._kokoro_map.clear()
        if previous in VOICEVOX_KEYS and engine not in VOICEVOX_KEYS:
            self._set_status("停止 VOICEVOX...", "starting")
            threading.Thread(target=self._stop_voicevox_worker, daemon=True).start()
        self.refresh_voices()
        self._persist()

    def _stop_voicevox_worker(self) -> None:
        self.voicevox_manager.stop_if_ours()
        self.logSignal.emit("VOICEVOX 已停止")

    def refresh(self) -> None:
        self.refresh_devices()
        self.refresh_voices()

    def refresh_devices(self) -> None:
        try:
            self.devices = list_output_devices()
        except Exception as exc:
            self.devices = []
            self._set_status(f"音频设备枚举失败: {exc}", "error")
            return

        self._outputs = []
        for index, device in enumerate(self.devices):
            label = f"{device.name} [{device.samplerate}Hz]"
            if label in self._outputs:
                label = f"{label} #{device.index}"
            self._outputs.append(label)

        hint = str(self.config.get("output_device", "") or "")
        target = find_device_by_hint(self.devices, hint)
        if target is None:
            target = find_device_by_hint(self.devices, "CABLE Input")
        if target is None:
            target = default_output_device(self.devices)

        monitor_hint = str(self.config.get("monitor_device", "") or "")
        monitor = find_device_by_hint(self.devices, monitor_hint)
        if monitor is None:
            monitor = default_output_device(self.devices)

        self._output_index = self.devices.index(target) if target in self.devices else -1
        self._monitor_index = self.devices.index(monitor) if monitor in self.devices else -1
        self.outputsChanged.emit()
        self.outputIndexChanged.emit()
        self.monitorIndexChanged.emit()
        if target is not None and "cable" not in target.name.lower():
            self._set_status("提示: 当前输出不是 CABLE，VRChat 可能收不到声音", "starting")

    def refresh_voices(self) -> None:
        engine = self.current_engine()
        if engine in ("edge", "edge_anime"):
            self._populate_edge()
            return
        if engine == "piper":
            self._populate_piper()
            return
        if engine == "kokoro":
            self._populate_kokoro()
            return
        self._set_status("启动/连接 VOICEVOX...", "starting")
        threading.Thread(target=self._fetch_voicevox, daemon=True).start()

    def _fetch_voicevox(self):
        if not self.voicevox_manager.ensure_started():
            self.voicesErrorSignal.emit("VOICEVOX 启动失败")
            return
        try:
            version = self.voicevox.version()
            items = flatten_speakers(self.voicevox.speakers())
            self.voicesSignal.emit((items, version))
        except Exception as exc:
            self.voicesErrorSignal.emit(str(exc))

    def _populate_edge(self) -> None:
        if not self.edge.available():
            self._set_voices(["Edge TTS 未安装"], 0)
            self._set_status("Edge TTS 未安装，请安装 edge-tts 和 soundfile", "error")
            return
        labels = [f"{name} · {voice}" for name, voice in EDGE_VOICES]
        self._edge_map = {
            label: voice for label, (_, voice) in zip(labels, EDGE_VOICES)
        }
        configured = str(self.config.get("edge_voice", DEFAULT_EDGE_VOICE))
        selected = next(
            (label for label, voice in self._edge_map.items() if voice == configured),
            0,
        )
        index = labels.index(selected) if selected in labels else 0
        self._set_voices(labels, index)
        label = "Edge TTS Anime" if self.current_engine() == EDGE_ANIME_KEY else "Edge TTS"
        self._set_status(f"{label}：{len(labels)} 个声音（需要网络）", "ready")

    def _populate_piper(self) -> None:
        items = self.piper.voices()
        self._piper_map = {label: path for label, path in items}
        labels = [label for label, _ in items]
        if not items:
            self._set_voices(["未找到模型"], 0)
            self._set_status(f"Piper 模型未找到，放到 {self.piper.models_dir}", "error")
            return
        configured = str(self.config.get("piper_model", ""))
        selected = next(
            (label for label, path in items if path == configured or label == configured),
            labels[0],
        )
        index = labels.index(selected)
        self._set_voices(labels, index)
        self._set_status(f"Piper：{len(labels)} 个本地模型", "ready")

    def _populate_kokoro(self) -> None:
        labels = [f"{name} · {voice}" for name, voice in KOKORO_VOICES]
        self._kokoro_map = {
            label: voice for label, (_, voice) in zip(labels, KOKORO_VOICES)
        }
        configured = str(self.config.get("kokoro_voice", "af_heart"))
        selected = next(
            (label for label, voice in self._kokoro_map.items() if voice == configured),
            labels[0],
        )
        index = labels.index(selected)
        self._set_voices(labels, index)
        if self.kokoro.available():
            self._set_status(
                "Kokoro：本地模型已就绪（首次使用会加载，CPU 较慢）",
                "ready",
            )
        else:
            self._set_status(f"Kokoro 模型未找到: {self.kokoro.model_path}", "error")

    def _on_voices(self, payload) -> None:
        if self.current_engine() not in VOICEVOX_KEYS:
            return
        items, version = payload
        self._speaker_map = {label: style_id for label, style_id in items}
        labels = [label for label, _ in items] or ["1"]
        configured = int(self.config.get("speaker", 1))
        matched = next(
            (
                label
                for label, style_id in self._speaker_map.items()
                if style_id == configured
            ),
            labels[0],
        )
        index = labels.index(matched) if matched in labels else 0
        self._set_voices(labels, index)
        label = "VOICEVOX 中文 (cn2kana)" if self.current_engine() == VOICEVOX_CN_KEY else "VOICEVOX"
        self._set_status(f"{label} {version}，{len(items)} 个声音", "ready")

    def _on_voices_error(self, message: str) -> None:
        if self.current_engine() not in VOICEVOX_KEYS:
            return
        configured = int(self.config.get("speaker", 1))
        self._speaker_map = {str(configured): configured}
        self._set_voices([str(configured)], 0)
        self._set_status(f"VOICEVOX 未连接: {message}", "error")

    def _set_voices(self, labels: list[str], index: int) -> None:
        self._voices = labels
        self._voice_index = max(0, min(len(labels) - 1, int(index)))
        self._current_voice = labels[self._voice_index] if labels else ""
        self.voicesChanged.emit()
        self.voiceIndexChanged.emit()
        self.currentVoiceChanged.emit()

    @Slot(int)
    def setEngine(self, index: int) -> None:
        self._set_engine_index(index)

    @Slot(int)
    def setVoice(self, index: int) -> None:
        self._set_voice_index(index)

    @Slot(int)
    def setOutput(self, index: int) -> None:
        self._set_output_index(index)

    @Slot(int)
    def setMonitorIndex(self, index: int) -> None:
        self._set_monitor_index(index)

    @Slot(float)
    def setSpeed(self, value: float) -> None:
        self._set_speed(value)

    @Slot(float)
    def setWindowAlpha(self, value: float) -> None:
        self._set_window_alpha(value)

    @Slot(str, bool)
    def setFlag(self, name: str, value: bool) -> None:
        if name == "chatbox":
            self._set_chatbox(value)
        elif name == "typing":
            self._set_typing(value)
        elif name == "output":
            self._set_output_enabled(value)
        elif name == "monitor":
            self._set_monitor(value)
        elif name == "hideAfterSend":
            self._set_hide_after_send(value)

    def _remember_voice(self) -> None:
        engine = self.current_engine()
        if engine in ("edge", "edge_anime"):
            self.config["edge_voice"] = self.get_edge_voice()
        elif engine == "piper":
            self.config["piper_model"] = self.get_piper_model()
        elif engine == "kokoro":
            self.config["kokoro_voice"] = self.get_kokoro_voice()
        else:
            self.config["speaker"] = self.get_speaker()
        self._persist()

    def get_edge_voice(self) -> str:
        raw = self._current_voice.strip()
        return self._edge_map.get(
            raw,
            raw or str(self.config.get("edge_voice", DEFAULT_EDGE_VOICE)),
        )

    def get_piper_model(self) -> str:
        raw = self._current_voice.strip()
        return self._piper_map.get(
            raw,
            raw or str(self.config.get("piper_model", "")),
        )

    def get_kokoro_voice(self) -> str:
        raw = self._current_voice.strip()
        return self._kokoro_map.get(
            raw,
            raw or str(self.config.get("kokoro_voice", "af_heart")),
        )

    def get_speaker(self) -> int:
        raw = self._current_voice.strip()
        if raw in self._speaker_map:
            return int(self._speaker_map[raw])
        try:
            return int(raw.split(":", 1)[0].strip())
        except Exception:
            return int(self.config.get("speaker", 1))

    def get_voice(self) -> str:
        engine = self.current_engine()
        if engine in ("edge", "edge_anime"):
            return self.get_edge_voice()
        if engine == "piper":
            return self.get_piper_model()
        if engine == "kokoro":
            return self.get_kokoro_voice()
        return str(self.get_speaker())

    def target_devices(self) -> list[Device]:
        devices: list[Device] = []
        if self._output_enabled and 0 <= self._output_index < len(self.devices):
            devices.append(self.devices[self._output_index])
        if self._monitor and 0 <= self._monitor_index < len(self.devices):
            monitor = self.devices[self._monitor_index]
            if all(device.index != monitor.index for device in devices):
                devices.append(monitor)
        if not devices and (self._output_enabled or self._monitor):
            fallback = default_output_device(self.devices)
            if fallback is not None:
                devices.append(fallback)
        return devices

    @Slot(str, result=bool)
    def send(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False
        max_chars = int(self.config.get("max_chars", 144))
        if len(text) > max_chars:
            result = ctypes.windll.user32.MessageBoxW(
                None,
                f"聊天框最多 {max_chars} 字符，将截断聊天框文字；语音仍读完整内容。继续？",
                APP_NAME,
                0x00000004 | 0x00000020 | 0x00040000,
            )
            if result != 6:
                return False
        chat_text = text[:max_chars] if self._chatbox else ""
        self._enqueue(
            {
                "text": text,
                "chat_text": chat_text,
                "engine": self.current_engine(),
                "voice": self.get_voice(),
                "speed": self._speed,
                "send_chatbox": self._chatbox,
                "devices": self.target_devices(),
            }
        )
        self._persist()
        if self._hide_after_send:
            self.hide()
        return True

    @Slot()
    def toggleExpanded(self) -> None:
        self._set_expanded(not self._expanded)

    @Slot()
    def refresh(self) -> None:
        self.refresh_devices()
        self.refresh_voices()

    @Slot(bool)
    def setTyping(self, active: bool) -> None:
        if not self._typing:
            if self._typing_sent:
                self._send_typing(False)
            return
        self._send_typing(bool(active))

    def _send_typing(self, active: bool) -> None:
        if active == self._typing_sent:
            return
        try:
            osc_send(self.osc, "/chatbox/typing", bool(active))
            self._typing_sent = bool(active)
        except Exception:
            pass

    def _enqueue(self, job: dict) -> None:
        self._busy = True
        self.jobs.put(job)
        self._set_status("合成中...", "starting")

    def worker_loop(self) -> None:
        while True:
            job = self.jobs.get()
            if job is None:
                return
            try:
                engine = job.get("engine", "voicevox")
                voice = str(job.get("voice", ""))
                speech_text = job["text"]
                if engine == VOICEVOX_CN_KEY:
                    speech_text = cn2kana.convert(speech_text)
                if engine in ("edge", "edge_anime"):
                    pitch = EDGE_ANIME_PITCH_HZ if engine == EDGE_ANIME_KEY else 0
                    wav = self.edge.synthesize(
                        job["text"],
                        voice,
                        job["speed"],
                        pitch_hz=pitch,
                    )
                elif engine == "piper":
                    wav = self.piper.synthesize(job["text"], voice, job["speed"])
                elif engine == "kokoro":
                    wav = self.kokoro.synthesize(job["text"], voice, job["speed"])
                else:
                    wav = self.voicevox.synthesize(speech_text, int(voice), job["speed"])
                pcm, samplerate = parse_wav(wav)
                if job["send_chatbox"] and job["chat_text"]:
                    osc_send(
                        self.osc,
                        "/chatbox/input",
                        job["chat_text"],
                        True,
                        False,
                    )
                self.logSignal.emit(
                    f"播放中... {len(pcm) / max(1, samplerate):.1f}s"
                )
                play_audio(pcm, samplerate, job["devices"])
                self.doneSignal.emit(job["text"])
            except Exception as exc:
                self.errorSignal.emit(f"{type(exc).__name__}: {exc}")

    @Slot()
    def hideWindow(self) -> None:
        self.hide()

    @Slot()
    def closeApp(self) -> None:
        self.close()

    def attach_window(self, window) -> None:
        self.window = window
        self._clamp_position()
        if not self.start_hidden:
            self.show()
        else:
            self.window.hide()

    def _screen_geometry(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _clamp_position(self) -> None:
        geometry = self._screen_geometry()
        if geometry is None:
            return
        height = EXPANDED_HEIGHT if self._expanded else COMPACT_HEIGHT
        width = WINDOW_WIDTH
        x = self._window_x
        y = self._window_y
        if x is None or y is None:
            x = geometry.right() - width - 40
            y = geometry.bottom() - height - 40
        x = max(geometry.left() + 8, min(int(x), geometry.right() - width - 8))
        y = max(geometry.top() + 8, min(int(y), geometry.bottom() - height - 8))
        self._window_x = x
        self._window_y = y
        if self.window is not None:
            self.window.setX(x)
            self.window.setY(y)

    @Slot(int, int)
    def saveWindowPosition(self, x: int, y: int) -> None:
        self._window_x = int(x)
        self._window_y = int(y)
        self.config["window_x"] = self._window_x
        self.config["window_y"] = self._window_y
        self._persist()

    def show(self) -> None:
        if self.window is None:
            return
        self.window.show()
        self.window.raise_()
        self.window.requestActivate()
        self.focusInput.emit()
        QTimer.singleShot(100, self.apply_window_style)

    def hide(self) -> None:
        if self.window is not None:
            self.window.hide()
        self._send_typing(False)

    def toggle_window(self) -> None:
        if self.window is not None and self.window.isVisible():
            self.hide()
        else:
            self.show()

    def close(self) -> None:
        self._send_typing(False)
        try:
            self.voicevox_manager.stop_if_ours()
        except Exception:
            pass
        self._persist()
        self.jobs.put(None)
        QGuiApplication.quit()

    def apply_window_style(self) -> None:
        if os.name != "nt" or self.window is None:
            return
        try:
            hwnd = int(self.window.winId())
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, -20)
            ex_style = (ex_style | 0x80) & ~0x40000
            user32.SetWindowLongW(hwnd, -20, ex_style)
            user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                0x0020 | 0x0002 | 0x0001 | 0x0004,
            )
            set_attribute = getattr(user32, "SetWindowCompositionAttribute", None)
            if set_attribute is not None:
                accent = AccentPolicy()
                accent.AccentState = 4
                accent.AccentFlags = 2
                accent.GradientColor = 0x66201812
                data = WindowCompositionAttributeData(
                    19,
                    ctypes.addressof(accent),
                    ctypes.sizeof(accent),
                )
                set_attribute(hwnd, ctypes.byref(data))
        except Exception:
            pass

    def _persist(self) -> None:
        self.config.update(
            {
                "speaker": self.get_speaker(),
                "speed_scale": self._speed,
                "window_alpha": self._window_alpha,
                "send_chatbox": self._chatbox,
                "send_typing": self._typing,
                "output_enabled": self._output_enabled,
                "monitor": self._monitor,
                "hide_after_send": self._hide_after_send,
                "tts_engine": self.current_engine(),
                "settings_expanded": self._expanded,
                "window_x": self._window_x,
                "window_y": self._window_y,
            }
        )
        engine = self.current_engine()
        if engine in ("edge", "edge_anime"):
            self.config["edge_voice"] = self.get_edge_voice()
        elif engine == "piper":
            self.config["piper_model"] = self.get_piper_model()
        elif engine == "kokoro":
            self.config["kokoro_voice"] = self.get_kokoro_voice()
        if self._device_explicit and 0 <= self._output_index < len(self.devices):
            self.config["output_device"] = self.devices[self._output_index].name
        if self._monitor_device_explicit and 0 <= self._monitor_index < len(self.devices):
            self.config["monitor_device"] = self.devices[self._monitor_index].name
        try:
            save_config(self.config_path, self.config)
        except Exception:
            pass


def cmd_check(config: dict) -> None:
    print("config:")
    print(json.dumps(config, ensure_ascii=False, indent=2))
    print("\noutput devices:")
    try:
        devices = list_output_devices()
        if not devices:
            print("  (none)")
        for device in devices:
            marker = "  <- CABLE" if "cable" in device.name.lower() else ""
            print(
                f"  [{device.index}] {device.name} "
                f"{device.samplerate}Hz {device.channels}ch{marker}"
            )
    except Exception as exc:
        print(f"  error: {exc}")

    print("\nvoicevox:")
    voicevox = Voicevox(
        str(config.get("voicevox_url", DEFAULT_CONFIG["voicevox_url"]))
    )
    try:
        print(f"  version: {voicevox.version()}")
        items = flatten_speakers(voicevox.speakers())
        print(f"  speakers: {len(items)}")
        for label, _ in items[:12]:
            print(f"    {label}")
    except Exception as exc:
        print(f"  unreachable: {exc}")

    piper = PiperTTS(
        str(config.get("piper_exe", PIPER_EXE)),
        str(config.get("piper_models_dir", PIPER_MODELS_DIR)),
    )
    kokoro = KokoroTTS(
        str(config.get("kokoro_model", KOKORO_MODEL)),
        str(config.get("kokoro_voices", KOKORO_VOICES_FILE)),
    )
    print(f"\nosc: {config.get('osc_host')}:{config.get('osc_port')}")
    print("hotkey: Ctrl+Alt+T (window)")
    print("tts engine:", config.get("tts_engine", "voicevox"))
    print("edge tts:", "available" if EdgeTTS.available() else "missing")
    print("piper exe:", piper.exe_path, "ok" if piper.available() else "missing")
    print("piper models:", len(piper.voices()), piper.models_dir)
    print("kokoro:", "ok" if kokoro.available() else "missing", kokoro.model_path)


def cmd_say(
    config: dict,
    text: str,
    speaker: int,
    speed: float,
    no_osc: bool,
    dry_run: bool = False,
    engine: str | None = None,
    voice: str | None = None,
) -> None:
    selected_engine = (engine or str(config.get("tts_engine", "voicevox"))).lower()
    speech_text = text
    if selected_engine == VOICEVOX_CN_KEY:
        speech_text = cn2kana.convert(text)
    if selected_engine in ("edge", "edge_anime"):
        edge = EdgeTTS(str(config.get("edge_proxy", "")))
        wav = edge.synthesize(
            text,
            voice or str(config.get("edge_voice", DEFAULT_EDGE_VOICE)),
            speed,
            pitch_hz=EDGE_ANIME_PITCH_HZ if selected_engine == EDGE_ANIME_KEY else 0,
        )
    elif selected_engine == "piper":
        piper = PiperTTS(
            str(config.get("piper_exe", PIPER_EXE)),
            str(config.get("piper_models_dir", PIPER_MODELS_DIR)),
        )
        models = piper.voices()
        model = voice or str(config.get("piper_model", ""))
        if not model or not Path(model).exists():
            model = next(
                (path for label, path in models if label == model),
                models[0][1] if models else "",
            )
        wav = piper.synthesize(text, model, speed)
    elif selected_engine == "kokoro":
        kokoro = KokoroTTS(
            str(config.get("kokoro_model", KOKORO_MODEL)),
            str(config.get("kokoro_voices", KOKORO_VOICES_FILE)),
        )
        wav = kokoro.synthesize(
            text,
            voice or str(config.get("kokoro_voice", "af_heart")),
            speed,
        )
    else:
        voicevox = Voicevox(
            str(config.get("voicevox_url", DEFAULT_CONFIG["voicevox_url"]))
        )
        wav = voicevox.synthesize(speech_text, speaker, speed)
    pcm, samplerate = parse_wav(wav)
    print(f"audio: {len(pcm) / max(1, samplerate):.2f}s, {samplerate}Hz")

    if dry_run:
        print("dry-run: skipped playback and OSC")
        return

    devices = list_output_devices()
    output = find_device_by_hint(devices, str(config.get("output_device", "")))
    if output is None:
        output = find_device_by_hint(devices, "CABLE Input")
    if output is None:
        output = default_output_device(devices)

    targets: list[Device] = []
    if bool(config.get("output_enabled", True)) and output is not None:
        targets.append(output)
    if bool(config.get("monitor", False)):
        monitor = find_device_by_hint(
            devices, str(config.get("monitor_device", ""))
        )
        if monitor is None:
            monitor = default_output_device(devices)
        if monitor is not None and all(
            device.index != monitor.index for device in targets
        ):
            targets.append(monitor)

    if not targets:
        raise RuntimeError("没有启用的输出设备")

    for target in targets:
        print(f"output: {target.name} ({target.samplerate}Hz)")
    if not no_osc:
        client = SimpleUDPClient(
            str(config.get("osc_host", "127.0.0.1")),
            int(config.get("osc_port", 9000)),
        )
        osc_send(
            client,
            "/chatbox/input",
            text[: int(config.get("max_chars", 144))],
            True,
            False,
        )
        print("sent: /chatbox/input")
    play_audio(pcm, samplerate, targets)
    print("done")


def main() -> int:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="VoiceBridge for VRChat")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--say")
    parser.add_argument("--no-osc", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--speaker", type=int)
    parser.add_argument("--speed", type=float)
    parser.add_argument("--engine", choices=ENGINE_KEYS)
    parser.add_argument("--voice")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--hidden", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    if config_path == CONFIG_PATH:
        migrate_old_data()
    config = load_config(config_path)

    if args.check:
        cmd_check(config)
        return 0

    if args.say:
        speaker = (
            args.speaker
            if args.speaker is not None
            else int(config.get("speaker", 1))
        )
        speed = (
            args.speed
            if args.speed is not None
            else float(config.get("speed_scale", 1.0))
        )
        cmd_say(
            config,
            args.say,
            speaker,
            speed,
            args.no_osc,
            args.dry_run,
            args.engine,
            args.voice,
        )
        return 0

    mutex = None
    if os.name == "nt" and not args.smoke:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_bool,
            ctypes.c_wchar_p,
        ]
        mutex = kernel32.CreateMutexW(None, False, "Local\\VoiceBridge")
        if kernel32.GetLastError() == 183:
            kernel32.CloseHandle(mutex)
            ctypes.windll.user32.MessageBoxW(
                None,
                "VoiceBridge 已在后台运行。\n按 Ctrl+Alt+T 显示主窗口。",
                APP_NAME,
                0x00000040 | 0x00040000,
            )
            return 0

    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    bridge = BridgeApp(config, config_path, start_hidden=args.hidden)
    engine.rootContext().setContextProperty("bridge", bridge)
    qml_path = data_paths()
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        ctypes.windll.user32.MessageBoxW(
            None,
            f"VoiceBridge 界面加载失败:\n{qml_path}",
            APP_NAME,
            0x00000010 | 0x00040000,
        )
        return 1

    bridge.attach_window(engine.rootObjects()[0])
    if args.smoke:
        QTimer.singleShot(2500, bridge.close)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
