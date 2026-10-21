import argparse
import asyncio
import ctypes
import io
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import requests
import sounddevice as sd
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.udp_client import SimpleUDPClient

try:
    import edge_tts
except Exception:
    edge_tts = None

try:
    import soundfile as sf
except Exception:
    sf = None


DEFAULT_EDGE_VOICE = "en-US-AvaMultilingualNeural"
VOICEVOX_ENGINE = "VOICEVOX"
EDGE_ENGINE = "Edge TTS"
PIPER_ENGINE = "Piper"
KOKORO_ENGINE = "Kokoro"
LOCAL_APP_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "VoiceBridge"
OLD_LOCAL_APP_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "VRChatVOICEVOXBridge"
PIPER_DIR = LOCAL_APP_DIR / "piper"
PIPER_MODELS_DIR = PIPER_DIR / "models"
PIPER_EXE = PIPER_DIR / "bin" / "piper" / "piper.exe"
KOKORO_DIR = LOCAL_APP_DIR / "kokoro"
KOKORO_MODEL = KOKORO_DIR / "kokoro-v1.0.int8.onnx"
KOKORO_VOICES_FILE = KOKORO_DIR / "voices-v1.0.bin"
KOKORO_VOICES = [
    ("Heart (US female)", "af_heart"),
    ("Bella (US female)", "af_bella"),
    ("Nicole (US female)", "af_nicole"),
    ("Sarah (US female)", "af_sarah"),
    ("Sky (US female)", "af_sky"),
    ("Emma (UK female)", "bf_emma"),
    ("Isabella (UK female)", "bf_isabella"),
    ("Xiaobei (CN female)", "zf_xiaobei"),
    ("Xiaoni (CN female)", "zf_xiaoni"),
    ("Xiaoxiao (CN female)", "zf_xiaoxiao"),
    ("Xiaoyi (CN female)", "zf_xiaoyi"),
    ("Alpha (JP female)", "jf_alpha"),
]
EDGE_VOICES = [
    ("Ava (US, multilingual)", "en-US-AvaMultilingualNeural"),
    ("Andrew (US, multilingual)", "en-US-AndrewMultilingualNeural"),
    ("Aria (US)", "en-US-AriaNeural"),
    ("Guy (US)", "en-US-GuyNeural"),
    ("Jenny (US)", "en-US-JennyNeural"),
    ("Sonia (UK)", "en-GB-SoniaNeural"),
    ("Ryan (UK)", "en-GB-RyanNeural"),
    ("Xiaoxiao (CN)", "zh-CN-XiaoxiaoNeural"),
    ("Yunxi (CN)", "zh-CN-YunxiNeural"),
    ("Nanami (JP)", "ja-JP-NanamiNeural"),
    ("Keita (JP)", "ja-JP-KeitaNeural"),
]


if getattr(sys, "frozen", False):
    APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "VoiceBridge"
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
OLD_APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "VRChatVOICEVOXBridge"
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "voicevox_url": "http://127.0.0.1:50021",
    "speaker": 1,
    "speed_scale": 1.0,
    "osc_host": "127.0.0.1",
    "osc_port": 9000,
    "output_device": "",
    "output_enabled": True,
    "monitor_device": "",
    "send_chatbox": True,
    "send_typing": True,
    "monitor": False,
    "hide_after_send": False,
    "max_chars": 144,
    "window_x": None,
    "window_y": None,
    "window_alpha": 0.70,
    "settings_expanded": False,
    "tts_engine": "voicevox",
    "edge_voice": DEFAULT_EDGE_VOICE,
    "edge_proxy": "http://127.0.0.1:19196",
    "piper_exe": str(PIPER_EXE),
    "piper_models_dir": str(PIPER_MODELS_DIR),
    "piper_model": "",
    "kokoro_model": str(KOKORO_MODEL),
    "kokoro_voices": str(KOKORO_VOICES_FILE),
    "kokoro_voice": "af_heart",
    "voicevox_engine_exe": "",
}

UI_BG = "#0D1117"
UI_HEADER = "#111827"
UI_PANEL = "#161B22"
UI_INPUT = "#0B0F14"
UI_BORDER = "#30363D"
UI_TEXT = "#E6EDF3"
UI_MUTED = "#8B949E"
UI_ACCENT = "#58A6FF"
UI_ACCENT_HOVER = "#79C0FF"
UI_ACCENT_DARK = "#0B1220"
UI_ACCENT2 = "#BC8CFF"
UI_BUTTON = "#21262D"
UI_BUTTON_HOVER = "#30363D"
UI_DANGER = "#F85149"
UI_OK = "#3FB950"
UI_FONT = ("Microsoft YaHei UI", 9)
UI_FONT_SMALL = ("Microsoft YaHei UI", 8)
UI_FONT_INPUT = ("Microsoft YaHei UI", 12)
UI_FONT_TITLE = ("Segoe UI Semibold", 12)


@dataclass(frozen=True)
class Device:
    index: int
    name: str
    samplerate: int
    channels: int


def load_config(path: Path) -> dict:
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update(data)
        except Exception:
            pass
    return config


def save_config(path: Path, config: dict) -> None:
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def list_output_devices(prefer_wasapi: bool = True) -> list[Device]:
    hostapis = []
    try:
        hostapis = sd.query_hostapis()
    except Exception:
        pass

    wasapi = None
    if prefer_wasapi:
        for index, api in enumerate(hostapis):
            if "WASAPI" in str(api.get("name", "")).upper():
                wasapi = index
                break

    devices = []
    for index, info in enumerate(sd.query_devices()):
        if int(info.get("max_output_channels", 0)) <= 0:
            continue
        if wasapi is not None and int(info.get("hostapi", -1)) != wasapi:
            continue
        devices.append(
            Device(
                index=index,
                name=str(info.get("name", f"device {index}")),
                samplerate=int(info.get("default_samplerate") or 48000),
                channels=int(info.get("max_output_channels", 2)),
            )
        )

    if devices:
        return devices

    for index, info in enumerate(sd.query_devices()):
        if int(info.get("max_output_channels", 0)) <= 0:
            continue
        devices.append(
            Device(
                index=index,
                name=str(info.get("name", f"device {index}")),
                samplerate=int(info.get("default_samplerate") or 48000),
                channels=int(info.get("max_output_channels", 2)),
            )
        )
    return devices


def default_output_index() -> Optional[int]:
    try:
        index = sd.default.device[1]
        if index is not None and int(index) >= 0:
            return int(index)
    except Exception:
        pass
    return None


def default_output_device(devices: list[Device]) -> Optional[Device]:
    if not devices:
        return None
    try:
        info = sd.query_devices(kind="output")
        name = str(info.get("name", ""))
        for device in devices:
            if device.name == name:
                return device
    except Exception:
        pass
    index = default_output_index()
    for device in devices:
        if device.index == index:
            return device
    return devices[0]


def find_device_by_hint(devices: list[Device], hint: str) -> Optional[Device]:
    if not hint:
        return None
    needle = hint.lower()
    for device in devices:
        if needle in device.name.lower():
            return device
    return None


class Voicevox:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = False

    def version(self) -> str:
        response = self.session.get(f"{self.base_url}/version", timeout=3)
        response.raise_for_status()
        return str(response.json())

    def speakers(self) -> list:
        response = self.session.get(f"{self.base_url}/speakers", timeout=5)
        response.raise_for_status()
        return response.json()

    def synthesize(self, text: str, speaker: int, speed: float) -> bytes:
        query_response = self.session.post(
            f"{self.base_url}/audio_query",
            params={"speaker": int(speaker), "text": text},
            timeout=20,
        )
        query_response.raise_for_status()
        query = query_response.json()
        query["speedScale"] = float(speed)

        audio_response = self.session.post(
            f"{self.base_url}/synthesis",
            params={"speaker": int(speaker)},
            json=query,
            timeout=180,
        )
        audio_response.raise_for_status()
        return audio_response.content


class EdgeTTS:
    def __init__(self, proxy: str = ""):
        self.proxy = (proxy or "").strip()

    @staticmethod
    def available() -> bool:
        return edge_tts is not None and sf is not None

    async def _fetch(
        self,
        text: str,
        voice: str,
        rate: str,
        proxy: str,
        pitch: str,
    ) -> bytes:
        kwargs = {}
        if proxy:
            kwargs["proxy"] = proxy
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            pitch=pitch,
            **kwargs,
        )
        data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data.extend(chunk["data"])
        return bytes(data)

    def synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch_hz: int = 0,
    ) -> bytes:
        if not self.available():
            raise RuntimeError("Edge TTS 未安装（需要 edge-tts 和 soundfile）")
        rate_value = int(round((float(speed) - 1.0) * 100))
        rate = f"{rate_value:+d}%"
        pitch = f"{int(pitch_hz):+d}Hz"
        try:
            mp3 = asyncio.run(
                self._fetch(text, voice, rate, self.proxy, pitch)
            )
        except Exception:
            if not self.proxy:
                raise
            mp3 = asyncio.run(self._fetch(text, voice, rate, "", pitch))
        if not mp3:
            raise RuntimeError("Edge TTS 没有返回音频")
        pcm, samplerate = sf.read(io.BytesIO(mp3), dtype="int16", always_2d=False)
        if isinstance(pcm, np.ndarray) and pcm.ndim > 1:
            pcm = pcm[:, 0]
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(int(samplerate))
            handle.writeframes(pcm.tobytes())
        return buffer.getvalue()


def wav_bytes(pcm: np.ndarray, samplerate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(samplerate))
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


class PiperTTS:
    def __init__(self, exe_path: str, models_dir: str):
        self.exe_path = Path(exe_path)
        self.models_dir = Path(models_dir)
        self.lock = threading.Lock()

    def available(self) -> bool:
        return self.exe_path.exists()

    def voices(self) -> list[tuple[str, str]]:
        if not self.models_dir.exists():
            return []
        items = []
        for model in sorted(self.models_dir.glob("*.onnx")):
            config = Path(str(model) + ".json")
            if config.exists():
                items.append((model.stem, str(model)))
        return items

    def synthesize(self, text: str, model_path: str, speed: float) -> bytes:
        if not self.available():
            raise RuntimeError(f"Piper 不存在: {self.exe_path}")
        if not model_path:
            raise RuntimeError("Piper 没有选择模型")
        model = Path(model_path)
        if not model.exists():
            raise RuntimeError(f"Piper 模型不存在: {model}")
        length_scale = 1.0 / max(0.5, min(2.0, float(speed)))
        temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output = Path(temp.name)
        temp.close()
        try:
            output.unlink(missing_ok=True)
            with self.lock:
                result = subprocess.run(
                    [
                        str(self.exe_path),
                        "--model",
                        str(model),
                        "--output_file",
                        str(output),
                        "--length_scale",
                        f"{length_scale:.3f}",
                    ],
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=120,
                    cwd=str(self.exe_path.parent),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            if result.returncode != 0 or not output.exists():
                detail = (result.stderr or result.stdout or "").strip().replace("\n", " ")
                raise RuntimeError(f"Piper 合成失败: {detail[:240]}")
            return output.read_bytes()
        finally:
            try:
                output.unlink()
            except Exception:
                pass


class KokoroTTS:
    def __init__(self, model_path: str, voices_path: str):
        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        self.kokoro = None
        self.lock = threading.Lock()

    def available(self) -> bool:
        return self.model_path.exists() and self.voices_path.exists()

    def ensure_loaded(self):
        with self.lock:
            if self.kokoro is not None:
                return self.kokoro
            if not self.available():
                raise RuntimeError(
                    f"Kokoro 模型未找到: {self.model_path} / {self.voices_path}"
                )
            os.environ["ONNX_PROVIDER"] = "CPUExecutionProvider"
            from kokoro_onnx import Kokoro

            self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
            return self.kokoro

    @staticmethod
    def language_for(voice: str) -> str:
        if voice.startswith(("zf", "zm")):
            return "zh"
        if voice.startswith(("jf", "jm")):
            return "ja"
        if voice.startswith(("bf", "bm")):
            return "en-gb"
        return "en-us"

    def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        kokoro = self.ensure_loaded()
        samples, samplerate = kokoro.create(
            text,
            voice=voice,
            speed=float(speed),
            lang=self.language_for(voice),
        )
        pcm = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)
        return wav_bytes(pcm, int(samplerate))


class VoicevoxManager:
    def __init__(self, client: Voicevox, exe_path: str = "", port: int = 50021):
        self.client = client
        self.port = port
        self.exe_path = Path(exe_path) if exe_path else self.default_exe()
        self.process = None
        self.started_by_us = False
        self.lock = threading.Lock()

    @staticmethod
    def default_exe() -> Path:
        local = os.getenv("LOCALAPPDATA", "")
        candidates = [
            Path(local) / "Programs" / "VOICEVOX" / "vv-engine" / "run.exe",
            Path("C:/Program Files/VOICEVOX/vv-engine/run.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def is_running(self) -> bool:
        try:
            self.client.version()
            return True
        except Exception:
            return False

    def ensure_started(self, timeout: float = 40.0) -> bool:
        with self.lock:
            if self.is_running():
                return True
            if not self.exe_path.exists():
                return False
            try:
                self.process = subprocess.Popen(
                    [str(self.exe_path), "--host", "127.0.0.1", "--port", str(self.port)],
                    cwd=str(self.exe_path.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                return False
            self.started_by_us = True
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.is_running():
                    return True
                if self.process.poll() is not None:
                    break
                time.sleep(0.5)
            return False

    def stop_if_ours(self) -> None:
        with self.lock:
            if not self.started_by_us or self.process is None:
                return
            pid = self.process.pid
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                try:
                    self.process.terminate()
                except Exception:
                    pass
            self.process = None
            self.started_by_us = False


def flatten_speakers(data: list) -> list[tuple[str, int]]:
    items = []
    for character in data:
        character_name = str(character.get("name", "?"))
        for style in character.get("styles", []):
            style_id = style.get("id")
            if style_id is None:
                continue
            style_name = str(style.get("name", ""))
            items.append((f"{style_id}: {character_name} / {style_name}", int(style_id)))
    return items


def parse_wav(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        samplerate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())

    if sample_width != 2:
        raise ValueError(f"unsupported sample width: {sample_width * 8} bit")

    pcm = np.frombuffer(raw, dtype="<i2").astype(np.int16, copy=False)
    if channels > 1:
        pcm = pcm.reshape(-1, channels)[:, 0].copy()
    return pcm, samplerate


def resample_linear(pcm: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or pcm.size == 0:
        return pcm.astype(np.int16, copy=False)

    target_size = max(1, int(round(pcm.size * target_rate / source_rate)))
    source_positions = np.arange(pcm.size, dtype=np.float64)
    target_positions = np.linspace(0.0, float(pcm.size - 1), target_size, dtype=np.float64)
    resampled = np.interp(target_positions, source_positions, pcm.astype(np.float32))
    return np.clip(resampled, -32768, 32767).astype(np.int16)


def play_on_device(pcm: np.ndarray, source_rate: int, device: Device, errors: list) -> None:
    try:
        samplerate = int(device.samplerate) or 48000
        data = resample_linear(pcm, source_rate, samplerate)
        channels = 2 if device.channels >= 2 else 1
        if channels == 2:
            data = np.column_stack((data, data)).astype(np.int16, copy=False)
        data = np.ascontiguousarray(data)
        with sd.OutputStream(
            samplerate=samplerate,
            channels=channels,
            dtype="int16",
            device=device.index,
        ) as stream:
            stream.write(data)
    except Exception as exc:
        errors.append(exc)


def play_audio(pcm: np.ndarray, samplerate: int, devices: list[Device]) -> None:
    if not devices:
        raise RuntimeError("没有可用的输出设备")
    errors = []
    threads = [
        threading.Thread(
            target=play_on_device,
            args=(pcm, samplerate, device, errors),
            daemon=True,
        )
        for device in devices
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        raise errors[0]


def osc_send(client: SimpleUDPClient, address: str, *args) -> None:
    builder = OscMessageBuilder(address=address)
    for arg in args:
        builder.add_arg(arg)
    client.send(builder.build())


class Hotkey(threading.Thread):
    def __init__(
        self,
        callback,
        modifiers: int = 0x0001 | 0x0002 | 0x4000,
        virtual_key: int = ord("T"),
        hotkey_id: int = 1,
    ):
        super().__init__(daemon=True)
        self.callback = callback
        self.modifiers = modifiers
        self.virtual_key = virtual_key
        self.hotkey_id = hotkey_id
        self.ok = threading.Event()
        self.failed = False

    def run(self) -> None:
        if os.name != "nt":
            self.failed = True
            self.ok.set()
            return

        from ctypes import wintypes

        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, self.hotkey_id, self.modifiers, self.virtual_key):
            self.failed = True
            self.ok.set()
            return

        self.ok.set()
        message = wintypes.MSG()
        try:
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result in (0, -1):
                    break
                if message.message == 0x0312 and message.wParam == self.hotkey_id:
                    self.callback()
        finally:
            user32.UnregisterHotKey(None, self.hotkey_id)


