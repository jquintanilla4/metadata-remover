# Metadata Remover

A desktop application that strips all metadata from video files using ffmpeg. Built with a dark-themed GUI via pywebview, it lets you drag and drop a video file (or browse/paste a path) and produces a clean copy with all metadata, chapters, and tags removed.

## How It Works

When you provide a video file, the app runs ffmpeg under the hood with the following flags:

```
ffmpeg -y -i input.mp4 -map_metadata -1 -map_chapters -1 -c copy output_clean.mp4
```

- `-map_metadata -1` — removes all global, stream, and chapter metadata
- `-map_chapters -1` — removes chapter markers
- `-c copy` — copies audio/video streams without re-encoding (fast, lossless)

The output file is saved next to the original with a `_clean` suffix. If that name already exists, it appends `_clean_1`, `_clean_2`, etc.

On first launch, the app checks whether ffmpeg is installed. If it's missing, it offers to install it automatically via Homebrew (macOS) or apt (Linux).

## Features

- **Drag & drop** video files directly onto the drop zone
- **Browse** your filesystem or paste a file path
- **New Session** button to quickly reset and process another file
- **Live output log** showing ffmpeg progress in a dark terminal-style panel
- **Auto-dependency install** — prompts to install ffmpeg if missing

## Supported Formats

`.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.3gp` `.ts`

## Prerequisites

- **Python 3.10+**
- [**uv**](https://docs.astral.sh/uv/) — fast Python package manager
- **ffmpeg** — the app will prompt to install this if missing

## Development

### Install dependencies and run

```bash
uv sync
make run
```

This runs `uv run python app.py`, which auto-installs dependencies into a virtual environment and launches the app.

### Project structure

```
app.py                  — entire application (single file)
pyproject.toml          — project metadata and dependencies
metadata_remover.spec   — PyInstaller build spec
build_app.sh            — assembles a macOS .app bundle from the binary
Makefile                — run/build/app/clean shortcuts
```

## Building a Standalone Binary

Build a self-contained executable using PyInstaller:

```bash
make build
```

This produces a single binary at `dist/metadata-remover`. The build:

1. Installs the `build` optional dependency group (PyInstaller)
2. Bundles the app + pywebview into one executable

### Building a macOS .app Bundle

To create a double-clickable `Metadata Remover.app`:

```bash
make app
```

This runs the PyInstaller build and then wraps the binary in a `.app` bundle at `dist/Metadata Remover.app`. To distribute it, zip it up:

```bash
cd dist
zip -r "Metadata Remover.zip" "Metadata Remover.app"
```

The recipient unzips and double-clicks the app. On first launch, macOS will block it since it's unsigned — they just need to right-click the app and select **Open** once to bypass Gatekeeper.

### Clean build artifacts

```bash
make clean
```

## Usage

### From source

```bash
make run
```

### Once the app is running

1. **Drag and drop** a video file onto the drop zone
2. Or **type/paste** a file path and click **Strip Metadata**
3. Or click **Browse** to select a file
4. The cleaned file appears next to the original with a `_clean` suffix
5. Click **New Session** to reset and process another file, or just drag a new file onto the drop zone

> **Note:** The end user needs ffmpeg installed on their system. The app will check for it on startup and offer to install it if missing (via Homebrew on macOS or apt on Linux). On Windows, ffmpeg must be installed manually and available in `PATH`.

## Libraries

| Library | Purpose |
| --- | --- |
| [pywebview](https://pywebview.flowrl.com/) | Lightweight cross-platform GUI using native webview |
| [PyInstaller](https://pyinstaller.org/) | Packages the app into a standalone executable (build-time only) |
| ffmpeg (system) | Performs the actual metadata stripping via subprocess |

## License

MIT
