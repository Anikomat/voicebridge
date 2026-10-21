# VoiceBridge

A desktop-mode text-to-speech bridge for VRChat, supporting VOICEVOX / VOICEVOX Chinese (cn2kana) / Edge TTS / Edge TTS Anime / Piper / Kokoro. The interface is a borderless, square-cornered, semi-transparent glass card.

## Quick Start

- Desktop shortcut: `VoiceBridge` (launches with `--hidden` by default)
- `Ctrl+Alt+T` to show / hide
- Type text in the input box, press `Enter` to send
- The send button is the blue `↑` on the right
- Before using "chatbox text" or "typing indicator", confirm OSC is enabled in VRChat's Action Menu → Options → OSC; voice goes through CABLE and does not depend on OSC
- Click `▾` on the bottom voice row to expand settings; the slider icon at the top right also expands them
- Settings, program, and model paths:
  - Config: `%APPDATA%\VoiceBridge\config.json`
  - Program: `%LOCALAPPDATA%\Programs\VoiceBridge\VoiceBridge.exe`
  - Piper: `%LOCALAPPDATA%\VoiceBridge\piper`
  - Kokoro: `%LOCALAPPDATA%\VoiceBridge\kokoro`

## Interface

- Borderless, square-cornered, semi-transparent glass card; no icon before the title
- DWM acrylic background + QML flowing highlight
- No system taskbar button, does not occupy Alt+Tab
- Compact mode shows only the input box and current voice
- Click `▾` or the top-right slider to expand engine, voice, speed, output, listen-in, and toggles
- `OUTPUT` and `LISTENIN` each have a checkbox and an independent device dropdown
- The window automatically stays on screen when expanded
- The `OPACITY` slider adjusts window transparency, range 25%–100%, config key `window_alpha`

## TTS Engines

- **VOICEVOX**: local engine, Japanese / anime-style voices; starts only when switched to, and stops automatically when switched away if it was started by this tool
- **VOICEVOX Chinese (cn2kana)**: uses `pypinyin` to convert Chinese characters to pinyin, then maps them to katakana for VOICEVOX; tones are lost, and polyphonic characters and English still need attention — the result is pinyin approximation rather than standard Mandarin
- **Edge TTS**: free online, English / Chinese / Japanese; requires network, default proxy `127.0.0.1:19196`
- **Edge TTS Anime**: anime-style voice variant of Edge TTS, pitch raised by `+50Hz`, otherwise identical to Edge TTS
- **Piper**: local lightweight, real-time on CPU; includes `en_US-amy-medium`, `en_US-lessac-medium`, `en_GB-jenny_dioco-medium`
- **Kokoro**: local 82M int8 model, more natural voices; slower on CPU, suitable for short sentences

VOICEVOX's `vv-engine\run.exe` is looked up by default at `%LOCALAPPDATA%\Programs\VOICEVOX\vv-engine\run.exe`; you can also set `voicevox_engine_exe` in the config.

## Key Configuration

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
  "monitor_device": "Headphones (your monitoring device)",
  "send_chatbox": false,
  "send_typing": true,
  "monitor": false,
  "hide_after_send": false,
  "window_alpha": 0.70,
  "settings_expanded": false
}
```

- Set `OUTPUT`'s `output_device` to `CABLE Input`, and VRChat's microphone to `CABLE Output`
- Set `LISTENIN`'s `monitor_device` to your own headphones/speakers, independent of CABLE
- `output_enabled` controls whether OUTPUT plays; `monitor` controls whether LISTENIN plays
- When both are on, audio plays to both devices simultaneously; when both are off, there is no sound
- When `send_chatbox` is off, audio only plays and no OSC text is sent

## Migrating from the Old Version

Formerly called `VRChat VOICEVOX Bridge`. On first launch, VoiceBridge will:

- Copy the old `%APPDATA%\VRChatVOICEVOXBridge\config.json` to the new config
- Rewrite old model paths to the new directories
- Migrate Piper/Kokoro models under `%LOCALAPPDATA%\VRChatVOICEVOXBridge`
- Keep a backup of the old config

## Development

```powershell
.\run.ps1
```

On first run it creates `.venv` and installs dependencies (including PySide6).

## Packaging

```powershell
pyinstaller --noconfirm --onedir --windowed --name "VoiceBridge" --icon app.ico `
  --add-data "ui;ui" `
  --collect-all soundfile --collect-all edge_tts --collect-all kokoro_onnx `
  --collect-all espeakng_loader --collect-all phonemizer --collect-all pypinyin --collect-all onnxruntime `
  --collect-all PySide6 --collect-all shiboken6 voicebridge.py
```

The packaged directory is about 780MB (mostly PySide6/Qt); startup is faster than onefile. Install location:
`%LOCALAPPDATA%\Programs\VoiceBridge\`.

## Troubleshooting

- **Piper cannot find `piper_phonemize.dll`**: the Piper directory is incomplete; re-extract `piper_windows_amd64.zip` into `%LOCALAPPDATA%\VoiceBridge\piper\bin\piper`
- **VOICEVOX not connected**: check the `vv-engine\run.exe` path, or open the VOICEVOX editor and try again
- **VRChat cannot hear**: output must be `CABLE Input`, VRChat's microphone must be `CABLE Output`, and the microphone must not be muted
- **Kokoro is very slow**: currently a CPU int8 model, long sentences are noticeably slow; for daily use, prefer Piper or Edge
- **Hotkey conflict**: `Ctrl+Alt+T` may be occupied by another program; the tool will show a hint in the status area

## Notes

- Voice enters VRChat's voice channel; players in the same room can hear it
- Edge TTS is a free online interface, fine for personal use; for commercial use, switch to Azure
- Do not commit API keys or private content from the config to the repository

## License

VoiceBridge is released under the **GNU GPL v3 or later**, see `LICENSE` and `COPYRIGHT`.
Third-party components in the release package, GPL/LGPL source locations, and external component notices are described in `THIRD_PARTY_NOTICES.md` and `SOURCE/` inside the release package.

---

# VoiceBridge（中文）

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

---

# VoiceBridge（日本語）

VRChat デスクトップモード用のテキスト読み上げブリッジ。VOICEVOX / VOICEVOX 中国語 (cn2kana) / Edge TTS / Edge TTS Anime / Piper / Kokoro に対応。UI は枠なし・直角・半透明のガラスカード。

## クイックスタート

- デスクトップショートカット：`VoiceBridge`（既定で `--hidden` 起動）
- `Ctrl+Alt+T` で表示 / 非表示
- 入力欄にテキストを入力し、`Enter` で送信
- 送信ボタンは右側の青い `↑`
- 「チャットボックス文字」または「タイピング表示」を使う前に、VRChat の Action Menu → Options → OSC で OSC が有効になっていることを確認；音声は CABLE 経由で、OSC には依存しない
- 下部の音色行の `▾` をクリックすると設定を展開；右上のスライダーアイコンでも展開可能
- 設定・プログラム・モデルのパス：
  - 設定：`%APPDATA%\VoiceBridge\config.json`
  - プログラム：`%LOCALAPPDATA%\Programs\VoiceBridge\VoiceBridge.exe`
  - Piper：`%LOCALAPPDATA%\VoiceBridge\piper`
  - Kokoro：`%LOCALAPPDATA%\VoiceBridge\kokoro`

## インターフェース

- 枠なし・直角・半透明のガラスカード。タイトル前にアイコンは表示しない
- DWM アクリル背景 + QML の流れるハイライト
- システムタスクバーボタンを表示せず、Alt+Tab も占有しない
- コンパクトモードでは入力欄と現在の音色のみ表示
- `▾` または右上のスライダーで、エンジン・音色・速度・出力・モニター・トグルを展開
- `OUTPUT` と `LISTENIN` にはそれぞれチェックボックスと独立したデバイスドロップダウンがある
- 展開時はウィンドウが自動的に画面内に収まる
- `OPACITY` スライダーでウィンドウの透明度を調整、範囲は 25%–100%、設定キーは `window_alpha`

## TTS エンジン

- **VOICEVOX**：ローカルエンジン、日本語 / アニメ系音声；切り替えたときのみ起動し、本ツールが起動した場合は切り替え時に自動停止
- **VOICEVOX 中国語 (cn2kana)**：`pypinyin` で漢字を拼音に変換し、片仮名にマッピングして VOICEVOX に渡す；声調は失われ、多音字や英語には注意が必要。聞こえ方は拼音近似であり、標準的な普通話ではない
- **Edge TTS**：無料オンライン、英語 / 中国語 / 日本語；ネットワークが必要、既定プロキシ `127.0.0.1:19196`
- **Edge TTS Anime**：Edge TTS のアニメ系音声バリアント。ピッチを `+50Hz` 上げ、それ以外は Edge TTS と同じ
- **Piper**：ローカル軽量、CPU でリアルタイム；`en_US-amy-medium`、`en_US-lessac-medium`、`en_GB-jenny_dioco-medium` を同梱
- **Kokoro**：ローカル 82M int8 モデル、より自然な音声；CPU では遅いため短い文に適する

VOICEVOX の `vv-engine\run.exe` は既定で `%LOCALAPPDATA%\Programs\VOICEVOX\vv-engine\run.exe` から検索。設定で `voicevox_engine_exe` を指定することも可能。

## 主要な設定

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
  "monitor_device": "ヘッドホン (モニター用デバイス)",
  "send_chatbox": false,
  "send_typing": true,
  "monitor": false,
  "hide_after_send": false,
  "window_alpha": 0.70,
  "settings_expanded": false
}
```

- `OUTPUT` の `output_device` は `CABLE Input`、VRChat のマイクは `CABLE Output` を選択
- `LISTENIN` の `monitor_device` は自分が聴くヘッドホン/スピーカーを選択。CABLE とは独立
- `output_enabled` は OUTPUT の再生可否、`monitor` は LISTENIN の再生可否を制御
- 両方オンにするとそれぞれのデバイスへ同時再生；両方オフにすると無音
- `send_chatbox` がオフの場合、音声のみで OSC テキストは送信しない

## 旧バージョンからの移行

以前は `VRChat VOICEVOX Bridge` という名前。VoiceBridge の初回起動時に：

- 旧 `%APPDATA%\VRChatVOICEVOXBridge\config.json` を新しい設定にコピー
- 旧モデルパスを新しいディレクトリに書き換え
- `%LOCALAPPDATA%\VRChatVOICEVOXBridge` 配下の Piper/Kokoro モデルを移行
- 旧設定のバックアップを保持

## 開発実行

```powershell
.\run.ps1
```

初回は `.venv` を作成し、依存関係（PySide6 を含む）をインストール。

## パッケージング

```powershell
pyinstaller --noconfirm --onedir --windowed --name "VoiceBridge" --icon app.ico `
  --add-data "ui;ui" `
  --collect-all soundfile --collect-all edge_tts --collect-all kokoro_onnx `
  --collect-all espeakng_loader --collect-all phonemizer --collect-all pypinyin --collect-all onnxruntime `
  --collect-all PySide6 --collect-all shiboken6 voicebridge.py
```

パッケージディレクトリは約 780MB（主に PySide6/Qt）。onefile より起動が速い。インストール先：
`%LOCALAPPDATA%\Programs\VoiceBridge\`。

## トラブルシューティング

- **Piper が `piper_phonemize.dll` を見つけられない**：Piper ディレクトリが不完全。`piper_windows_amd64.zip` を `%LOCALAPPDATA%\VoiceBridge\piper\bin\piper` に再解凍
- **VOICEVOX に接続できない**：`vv-engine\run.exe` のパスを確認するか、VOICEVOX エディタを開いてから再試行
- **VRChat で聞こえない**：出力は `CABLE Input`、VRChat のマイクは `CABLE Output`、マイクがミュートでないことを確認
- **Kokoro が非常に遅い**：現在は CPU int8 モデルのため長文は明らかに遅い。日常用途は Piper か Edge を推奨
- **ホットキー競合**：`Ctrl+Alt+T` が他のプログラムに占有されている可能性。ツールがステータスにヒントを表示

## 注意

- 音声は VRChat の音声チャンネルに入り、同じルームのプレイヤーに聞こえる
- Edge TTS は無料オンラインインターフェース。個人利用は可、商用利用は Azure に切り替えること
- API キーや設定内のプライベート情報をリポジトリにコミットしないこと

## ライセンス

VoiceBridge は **GNU GPL v3 以降**で公開。`LICENSE` と `COPYRIGHT` を参照。
リリースパッケージ内のサードパーティコンポーネント、GPL/LGPL ソースの場所、外部コンポーネントの説明は、リリースパッケージ内の `THIRD_PARTY_NOTICES.md` と `SOURCE/` を参照。
