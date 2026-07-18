# YouTube 字幕抓取与视频总结

这是一个纯 Python 命令行项目，不包含网页端。它可以从 YouTube 链接获取字幕，将所有字幕片段连同起止时间保存为 UTF-8 文本；项目同时提供一个 Local Codex Skill，用字幕提炼视频的完整内容。

## 项目结构

```text
.
├── youtube_transcript.py
├── requirements.txt
└── .codex/skills/youtube-video-summary/
    ├── SKILL.md
    ├── agents/openai.yaml
    └── scripts/
        ├── youtube_transcript.py
        └── requirements.txt
```

## 安装

建议使用 Python 3.10 或更高版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Windows 激活虚拟环境时使用：

```powershell
.venv\Scripts\activate
```

## 导出字幕

自动选择视频的原始字幕轨道：

```bash
python3 youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

指定输出路径：

```bash
python3 youtube_transcript.py "YOUTUBE_URL" --output transcript.txt
```

查看可用语言并指定字幕轨道：

```bash
python3 youtube_transcript.py "YOUTUBE_URL" --list-languages
python3 youtube_transcript.py "YOUTUBE_URL" --language zh-Hans --output transcript_zh.txt
```

每条字幕采用以下格式：

```text
[00:00:00.000 --> 00:00:05.160] caption text
```

## 使用 Local Skill 总结视频

Local Skill 位于 `.codex/skills/youtube-video-summary/`。在这个项目中调用 `$youtube-video-summary` 并附上 YouTube 链接，Codex 会运行同一套 Python 字幕脚本，完整读取字幕，然后按主题提炼视频内容。

Skill 的最终总结默认不包含时间线或 timestamp，也不会逐条复述字幕。

## 注意

YouTube 没有字幕或限制字幕访问时，脚本会以非零状态退出并显示错误。自动字幕的准确度取决于 YouTube 本身。
