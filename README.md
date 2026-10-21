# VoiceBridge

VRChat 桌面模式文字转语音桥，支持 VOICEVOX / VOICEVOX 中文 (cn2kana) / Edge TTS / Edge TTS Anime / Piper / Kokoro，界面为无边框直角半透明玻璃卡片。

## 快速使用

- 桌面快捷方式：`VoiceBridge`（默认 `--hidden` 启动）
- `Ctrl+Alt+T` 显示 / 隐藏
- 在输入框输入文字，`Enter` 发送
- 发送按钮是右侧蓝色 `↑`
- 使用“聊天框文字”或“打字指示”前，在 VRChat 的 Action Menu → Options → OSC 中确认 OSC 已开启；语音走 CABLE，不依赖 OSC
- 底部音色行点 `▾` 展开设置；右上滑杆图标也可以展开
- 设置、程序、模型路径：
  - 配置：`%APPDATA%\VoiceBridge\config.json`
  - 程序：`%LOCALAPPDATA%\Programs\VoiceBridge\VoiceBridge.exe`
  - Piper：`%LOCALAPPDATA%\VoiceBridge\piper`
  - Kokoro：`%LOCALAPPDATA%\VoiceBridge\kokoro`

## 界面

- 无边框、直角、半透明玻璃卡片，标题前不显示图标
- DWM 亚克力背景 + QML 流光高光
- 不显示系统任务栏按钮，不占 Alt+Tab
- 紧凑模式只显示输入框和当前音色
- 点 `▾` 或右上滑杆展开引擎、音色、语速、输出、监听和开关
- `OUTPUT` 和 `LISTENIN` 各有一个复选框和独立设备下拉框
- 展开时窗口自动保持在屏幕内
- `OPACITY` 滑杆可调整窗口透明度，范围 25%–100%，配置项为 `window_alpha`

## TTS 引擎

- **VOICEVOX**：本地引擎，日文/二次元音色；切到它时才启动，切走时如果是本工具启动的会自动停止
- **VOICEVOX 中文 (cn2kana)**：先用 `pypinyin` 把汉字转成拼音，再映射成片假名交给 VOICEVOX；声调会丢失，多音字和英文仍需注意，听感是拼音近似而不是标准普通话
- **Edge TTS**：免费在线，英文/中文/日文；需要网络，默认代理 `127.0.0.1:19196`
- **Edge TTS Anime**：Edge TTS 的二次元音色变体，音高提高 `+50Hz`，其余与 Edge TTS 相同
- **Piper**：本地轻量，CPU 实时；已带 `en_US-amy-medium`、`en_US-lessac-medium`、`en_GB-jenny_dioco-medium`
- **Kokoro**：本地 82M int8 模型，音色更自然；CPU 较慢，适合短句

VOICEVOX 的 `vv-engine\run.exe` 默认从 `%LOCALAPPDATA%\Programs\VOICEVOX\vv-engine\run.exe` 查找，也可以在配置里写 `voicevox_engine_exe`。

## 关键配置

```json
{
  "tts_engine": "voicevox",
  "speaker": 2,
  "edge_voice": "en-US-AvaMultilingualNeural",
  "edge_proxy": "http://127.0.0.1:19196",
  "piper_exe": "C:\\Users\\<you>\\AppData\\Local\\VoiceBridge\\piper\\bin\\piper\\piper.exe",
  "piper_models_dir": "C:\\Users\\<you>\\AppData\\Local\\VoiceBridge\\piper\\models",
  "piper_model": "",
  "kokoro_model": "C:\\Users\\<you>\\AppData\\Local\\VoiceBridge\\kokoro\\kokoro-v1.0.int8.onnx",
  "kokoro_voices": "C:\\Users\\<you>\\AppData\\Local\\VoiceBridge\\kokoro\\voices-v1.0.bin",
  "kokoro_voice": "af_heart",
  "output_device": "CABLE Input",
  "output_enabled": true,
  "monitor_device": "耳机 (你的监听设备)",
  "send_chatbox": false,
  "send_typing": true,
  "monitor": false,
  "hide_after_send": false,
  "window_alpha": 0.70,
  "settings_expanded": false
}
```

- `OUTPUT` 的 `output_device` 选 `CABLE Input`，VRChat 麦克风选 `CABLE Output`
- `LISTENIN` 的 `monitor_device` 选自己听的耳机/扬声器，和 CABLE 相互独立
- `output_enabled` 控制 OUTPUT 是否播放，`monitor` 控制 LISTENIN 是否播放
- 两个都开启时会同时播放到各自设备；两个都关闭则没有声音
- `send_chatbox` 关闭时只出声，不发 OSC 文字

## 从旧版迁移

以前叫 `VRChat VOICEVOX Bridge`。首次启动 VoiceBridge 会：

- 复制旧 `%APPDATA%\VRChatVOICEVOXBridge\config.json` 到新配置
- 把旧模型路径改写到新目录
- 迁移 `%LOCALAPPDATA%\VRChatVOICEVOXBridge` 下的 Piper/Kokoro 模型
- 旧配置保留备份

## 开发运行

```powershell
.\run.ps1
```

首次会创建 `.venv` 并安装依赖（包含 PySide6）。

## 打包

```powershell
pyinstaller --noconfirm --onedir --windowed --name "VoiceBridge" --icon app.ico `
  --add-data "ui;ui" `
  --collect-all soundfile --collect-all edge_tts --collect-all kokoro_onnx `
  --collect-all espeakng_loader --collect-all phonemizer --collect-all pypinyin --collect-all onnxruntime `
  --collect-all PySide6 --collect-all shiboken6 voicebridge.py
```

打包目录约 780MB（主要是 PySide6/Qt），启动比 onefile 快。安装位置：
`%LOCALAPPDATA%\Programs\VoiceBridge\`。

## 排错

- **Piper 找不到 `piper_phonemize.dll`**：Piper 目录不完整，重新解压 `piper_windows_amd64.zip` 到 `%LOCALAPPDATA%\VoiceBridge\piper\bin\piper`
- **VOICEVOX 未连接**：检查 `vv-engine\run.exe` 路径，或打开 VOICEVOX 编辑器后再试
- **VRChat 听不到**：输出必须是 `CABLE Input`，VRChat 麦克风必须是 `CABLE Output`，麦克风不能静音
- **Kokoro 很慢**：当前是 CPU int8 模型，长句会明显慢；日常建议 Piper 或 Edge
- **热键冲突**：`Ctrl+Alt+T` 可能被其它程序占用，工具会在状态里提示

## 注意

- 语音会进入 VRChat 语音通道，同房间玩家能听到
- Edge TTS 是免费在线接口，个人使用可以，商用请改用 Azure
- 不要把 API key、配置里的隐私内容提交到仓库

## 许可证

VoiceBridge 以 **GNU GPL v3 或更高版本**发布，见 `LICENSE` 和 `COPYRIGHT`。
发布包中的第三方组件、GPL/LGPL 源码位置和外部组件说明见发布包内的
`THIRD_PARTY_NOTICES.md` 与 `SOURCE/`。




