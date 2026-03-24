# Metadata Remover

A terminal UI (TUI) application that strips all metadata from video files using ffmpeg. Built with a cyberpunk-themed interface, it lets you drag and drop a video file (or browse/paste a path) and produces a clean copy with all metadata, chapters, and tags removed.

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
2. Bundles the app + Textual data files into one executable

### Building a macOS .app Bundle

To create a double-clickable `Metadata Remover.app` that opens Terminal and launches the TUI:

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

### From the built binary

After running `make build`, you'll find a single standalone executable at:

```
dist/metadata-remover
```

This is **not** a `.app` bundle or `.exe` installer — it's a single, fully self-contained command-line binary. No Python installation required, no extra files or folders needed. You can move it anywhere you like — your Desktop, Downloads, or a folder on your `$PATH`.

It's a terminal app, so it needs to be launched from a terminal:

**macOS / Linux:**

1. Open **Terminal** (or iTerm, Warp, etc.)
2. Drag the `metadata-remover` binary into the terminal window — this pastes its path
3. Press Enter to launch

Or run it from wherever you put it:

```bash
./metadata-remover
```

To make it available system-wide (run from any directory):

```bash
cp dist/metadata-remover /usr/local/bin/
metadata-remover
```

**Windows:**

The binary will be named `metadata-remover.exe`. Open **Command Prompt** or **PowerShell** and run:

```powershell
.\dist\metadata-remover.exe
```

> **Note:** The end user still needs ffmpeg installed on their system. The app will check for it on startup and offer to install it if missing (via Homebrew on macOS or apt on Linux). On Windows, ffmpeg must be installed manually and available in `PATH`.

### Once the app is running

1. **Drag and drop** a video file into the terminal window — the app detects the path automatically and starts stripping metadata
2. Or **type/paste** a file path into the input field and click **Strip Metadata**
3. Or click **Browse** to navigate your filesystem and select a file
4. The cleaned file appears next to the original with a `_clean` suffix

## Libraries

| Library | Purpose |
| --- | --- |
| [Textual](https://textual.textualize.io/) | TUI framework — widgets, screens, layout, event handling, theming |
| [Rich](https://rich.readthedocs.io/) | Terminal rendering (used internally by Textual for styled text and segments) |
| [PyInstaller](https://pyinstaller.org/) | Packages the app into a standalone executable (build-time only) |
| ffmpeg (system) | Performs the actual metadata stripping via subprocess |

## License

MIT