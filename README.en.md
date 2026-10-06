<div align="center">

<img src="logo.jpeg" alt="DayLens Logo" width="128" height="128">

# DayLens

### Turn raw computer activity into "what I actually did today"

[![License: MIT](https://img.shields.io/badge/License-MIT-2D7FF9.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D4.svg?logo=windows&logoColor=white)](https://github.com/xueze-ai/daylens)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/Qt-PySide6%206.8-41CD52.svg?logo=qt&logoColor=white)](https://www.qt.io/)
[![Version](https://img.shields.io/badge/Version-v1.0.9-success.svg)](https://github.com/xueze-ai/daylens/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-F59E0B.svg)#contributing)

[简体中文](README.md) ｜ **English**

</div>

---

## Introduction

**DayLens** is a **local-first** personal activity review tool for Windows. It quietly records foreground app usage, file changes, browser activity, software installations and files received via WeChat, then merges tens of thousands of low-level records into a single, easy-to-read answer: **"What did I do today?"**

It also builds an all-day timeline, a focus score, snapshot diffs, and an AI-written daily review powered by your own AI service.

> DayLens is **not** a screen recorder or a keylogger. It never captures screenshots, audio, keystrokes, or WeChat chat content. By default, every piece of data stays on your own computer.

## Preview

### Feature overview (1/2)

![Feature overview 1](docs/images/preview-grid-1.png)

### Feature overview (2/2)

![Feature overview 2](docs/images/preview-grid-2.png)

### Page details

**Today overview**: active time, number of apps, file changes and AI-grouped events at a glance, followed by the 0–24 h timeline and focus score.

![Today overview](docs/images/01-overview.png)

**AI daily review**: structured evidence is turned into a concise report, and every claim can be traced back to the evidence below. "Opened" is never written as "completed".

![AI daily review](docs/images/02-ai-review.png)

**App usage & web browsing**: apps are ranked by real foreground time; websites are aggregated by domain with visit counts, and page titles are available on hover/expand.

![App usage and web browsing](docs/images/03-apps-browser.png)

**Things done**: file noise from the same project, software folder or download folder is merged into a single activity, with expandable file evidence preserved.

![Things done](docs/images/04-activities.png)

**Full Today page**: every module in one image (scroll inside the window to explore).

![Full Today page](docs/images/05-today-full.png)

**WeChat files**: type, size and notes listed by receive time, with type filters; AI summaries are available for documents after configuration. Senders and chat content cannot be obtained and are never fabricated.

![WeChat files](docs/images/06-wechat.png)

**Snapshot compare**: compare additions, modifications, deletions and size changes between two points in time, with action/type/path filters and an optional AI interpretation.

![Snapshot compare](docs/images/07-snapshot-diff.png)

**Daily records**: local and AI summaries archived by date, with weekly/monthly reports and the ability to re-push a selected day's report.

![Daily records](docs/images/08-history.png)

**AI settings**: both OpenAI-compatible APIs and local Ollama are supported; connection tests run in the background.

![AI settings](docs/images/09-settings-ai.png)

**About page**: version, author, technical stack and data principles are clearly documented.

![About page](docs/images/10-about.png)

**Dark mode**: both the main window and settings offer light and dark themes.

![Dark mode](docs/images/11-dark.png)

> All names, files, websites and data shown in the screenshots are demo data.

## Features

- **App usage time**: samples the current foreground window every 5 seconds and merges continuous use into sessions for accurate foreground time.
- **File change monitoring**: watches selected drives via Windows file-system events and batches them into SQLite — no 15,000-record cap.
- **Semantic activity grouping**: merges file noise from the same project, software folder or download folder into a single activity.
- **Software installation detection**: compares the Windows installed-software list to detect installs, updates and uninstalls.
- **Browser history overview**: reads local Chrome, Edge and Firefox history and aggregates visits by domain.
- **WeChat file monitoring**: records new files in the WeChat receive folder, with categories, notes and AI summaries for selected documents.
- **All-day timeline**: 0–24 h color blocks for app sessions and idle time, with wheel zoom, dragging and second-precise hover tooltips.
- **Focus analysis**: a 0–100 score, switch count, and average/longest continuous usage.
- **Auto/manual snapshots**: compare file additions, modifications, deletions and size changes between two points in time.
- **AI daily review**: any OpenAI-compatible API or local Ollama can turn structured evidence into a natural-language report.
- **Automatic daily report**: generate a summary at a set time and optionally push it to WeChat via ServerChan.
- **Global search & quick notes**: search files, WeChat files, AI summaries and notes; press `Ctrl+Alt+N` to jot down an idea.
- **Light/dark themes & single instance**: double-clicking again activates the existing window instead of spawning another monitor process.

## Quick Start

### Option 1: Download a release (recommended for users)

1. Go to the [Releases page](https://github.com/xueze-ai/daylens/releases) and download the latest `DayLens_vX.Y.Z-Windows-x64.zip`.
2. Extract it, keep the complete folder together, and double-click `DayLens_vX.Y.Z.exe` (do not copy the EXE alone or move the `_internal` folder).
3. On the first launch, local configuration and a database are created, and activity recording begins.
4. Closing the main window keeps the app in the system tray; double-click the tray icon to reopen it, and right-click → "Exit" to close it completely.

**Windows SmartScreen warning**: the app does not yet have a commercial code-signing certificate, so "Windows protected your PC" may appear. After confirming the source is this project, click "More info → Run anyway".

### Option 2: Run from source (recommended for developers)

Requirements: **Python 3.11** (Windows 10 / 11, 64-bit).

```powershell
git clone https://github.com/xueze-ai/daylens.git
cd daylens/DayLens

# Use the bundled setup script to create the venv (uv required):
powershell -ExecutionPolicy Bypass -File .\setup-build.ps1

# Or create it manually:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run
python main.py
```

### Option 3: Build the EXE yourself

With the virtual environment activated in the `DayLens` directory:

```powershell
.\build.bat
```

The output goes to `dist\DayLens_vX.Y.Z\`. To include the logo, the PyInstaller arguments contain:

```text
--icon assets\logo.ico
--add-data "assets\logo.png;assets"
```

Exit the running DayLens from the tray before building, or the output directory may be locked.

## First-run tips

1. Confirm the drives to monitor under "Settings → General".
2. Set the idle threshold (default: 5 minutes).
3. Under "Settings → Data sources", confirm browser-history collection and the WeChat file folder; disable features you don't need.
4. For AI summaries, configure an OpenAI-compatible API or local Ollama under "Settings → AI service".
5. Keep the app running for a while, then check app usage, the timeline and the focus score.

App usage time accumulates only after DayLens starts and cannot be backfilled from before installation; browser history and the file baseline can read existing information on the machine.

## Privacy & Security

Configuration, database and logs are all stored locally:

```text
%APPDATA%\DayLens\config.json
%APPDATA%\DayLens\daylens.db
%APPDATA%\DayLens\logs\
```

**What the AI receives**: only when you actively generate a summary does the app send limited, pre-aggregated data to the AI endpoint **you configured** — app names with foreground seconds, session counts, truncated sample window titles, up to 60 activity clusters, up to 10 browser-domain summaries, the focus score and the date.

- The complete raw file list or file contents are **never** sent by default.
- Actual document text is read and sent only when you click "Analyze" on a WeChat document (up to about 30,000 characters); for PDFs, the first and last pages are preferred.
- App usage, file grouping, browser overview, snapshots and local rule-based summaries all work without any AI configured.
- Credentials are stored in local JSON under the current Windows user. Never commit `config.json`, the database or logs to a public repository or share them with others.

## How it works

```text
Foreground sampling → app sessions & usage ─┐
File-system events → project/app/download… ─┤
Install-list changes → install/update/rem… ─┤
Browser history ───→ domain summaries ──────┤
WeChat receive dir → file type & records ──┤
Idle detection ────→ focus score & timeli… ─┤
                                             ├─→ local rule-based summary
Snapshot A + B ───→ add/modify/delete diff ┘
                                             └─→ on-demand AI → daily review
```

File events and samples are stored first (SQLite in WAL mode), then de-duplicated, aggregated and rendered on demand; the network AI is not part of the monitoring pipeline.

## FAQ

**No app usage after a long time?** Make sure DayLens is still in the tray, click "Refresh", and actively use a few apps for at least one minute; check the logs if it is still empty.

**Web browsing stays empty?** Confirm browser-history collection is enabled; incognito pages are not saved, and portable browsers or custom user-data directories may not be detected.

**Multiple windows appear?** Single-instance is enforced; if it still happens, an older and a newer build are likely running from different folders. Check the EXE path in Task Manager and exit the old one.

**AI returns 401 / is very slow?** 401 means the key is invalid, expired or not valid for this service — verify the API URL, key and model permissions; speed depends on the network, service load or local Ollama hardware.

**Why does it keep running after I close the window?** Closing the window only hides it to the tray while monitoring continues; right-click the tray icon and choose "Exit" to close it fully.

<details>
<summary><b>More questions & known limitations</b></summary>

- Foreground time before installing DayLens cannot be recovered.
- File changes do not prove with absolute certainty that the user performed the work.
- WeChat senders, group names and chat content are unavailable.
- Protected directories may not be readable or snapshot-able due to permissions.
- AI output is only an aid for review and should not be used as audit or legal evidence.

</details>

## Contributing

Issues and pull requests are welcome:

1. Fork the repository and create a feature branch (`git checkout -b feature/awesome-feature`).
2. Make your changes and ensure basic checks pass.
3. Commit your changes (`git commit -m "feat: add awesome feature"`).
4. Push the branch and open a pull request, clearly describing what and why.

When filing a bug, please include the OS version, DayLens version, reproduction steps and logs (redact sensitive information first — never paste API keys).

## Roadmap

- History collection for more browsers (Brave, Opera and Chromium-based regional browsers).
- Richer timeline statistics and export styles.
- Pluggable review templates and more push channels.

## Usage principles

Only run DayLens on computer accounts you are authorized to use and monitor; on shared computers, respect other users' right to know and their privacy.

## License

This project is open-sourced under the [MIT License](LICENSE).

<div align="center">

**DayLens** — see every day clearly, and spend your time on what truly matters.

</div>
