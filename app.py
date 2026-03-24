"""Metadata Remover — strip metadata from video files using ffmpeg."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.theme import Theme
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import (
    Button,
    DirectoryTree,
    Input,
    ProgressBar,
    RichLog,
    Static,
)

from rich.segment import Segment
from rich.style import Style


class GridBackground(Widget):
    """Fills the screen with a repeating + grid pattern."""

    DEFAULT_CSS = """
    GridBackground {
        width: 1fr;
        height: 1fr;
        layer: below;
    }
    """

    GRID_X = 6   # horizontal chars between +
    GRID_Y = 3   # vertical rows between + (approx square with 2:1 char ratio)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        style = Style(color="#222222")
        if y % self.GRID_Y == 0:
            text = "".join("+" if x % self.GRID_X == 0 else " " for x in range(width))
            return Strip([Segment(text, style)])
        return Strip([Segment(" " * width, style)])

CYBER_THEME = Theme(
    name="cyberpunk",
    primary="#ff2a6d",       # hot pink / neon magenta
    secondary="#05d9e8",     # electric cyan
    accent="#d300c5",        # neon purple
    foreground="#d1f7ff",    # pale ice blue
    background="#000000",    # pure black
    success="#00ff9f",       # neon green
    warning="#f9f002",       # neon yellow
    error="#ff2a6d",         # hot pink
    surface="#12121e",       # dark panel
    panel="#1a1a2e",         # slightly lighter panel
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-background": "#12121e",
        "footer-key-foreground": "#05d9e8",
        "footer-key-background": "#1a1a2e",
        "footer-description-foreground": "#d1f7ff 70%",
        "footer-description-background": "#12121e",
        "input-cursor-foreground": "#ff2a6d",
        "input-selection-background": "#d300c5 30%",
        "scrollbar-color": "#05d9e8 30%",
        "scrollbar-color-hover": "#05d9e8 60%",
        "scrollbar-color-active": "#ff2a6d",
    },
)

SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
}


def get_output_path(input_path: Path) -> Path:
    """Return a non-colliding *_clean* output path next to the original."""
    output = input_path.with_stem(f"{input_path.stem}_clean")
    counter = 1
    while output.exists():
        output = input_path.with_stem(f"{input_path.stem}_clean_{counter}")
        counter += 1
    return output


def validate_video_file(path_str: str) -> Path | str:
    """Return the resolved Path on success, or an error string on failure."""
    if not path_str.strip():
        return "No file path provided."
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        return f"File not found: {p}"
    if not p.is_file():
        return f"Not a file: {p}"
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return f"Unsupported format '{p.suffix}'. Supported: {exts}"
    if not os.access(p, os.R_OK):
        return f"Permission denied (cannot read): {p}"
    if not os.access(p.parent, os.W_OK):
        return f"Permission denied (cannot write to directory): {p.parent}"
    return p


def find_brew() -> str | None:
    """Return the path to brew, checking common locations."""
    brew = shutil.which("brew")
    if brew:
        return brew
    for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None



class ConfirmScreen(Screen[bool]):
    """A reusable yes / no confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-box {
        width: 60;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        background: $surface;
    }
    #confirm-message {
        width: 100%;
        margin-bottom: 1;
        text-align: center;
        color: $foreground;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    #confirm-buttons Button {
        margin: 0 2;
        background: $panel;
        color: $foreground;
        border: none;
        min-width: 12;
        text-style: bold;
    }
    #confirm-buttons #yes {
        background: $success 20%;
        color: $success;
    }
    #confirm-buttons #yes:hover {
        background: $success 35%;
    }
    #confirm-buttons #no {
        background: $error 20%;
        color: $error;
    }
    #confirm-buttons #no:hover {
        background: $error 35%;
    }
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", id="yes", variant="success")
                yield Button("No", id="no", variant="error")

    @on(Button.Pressed, "#yes")
    def handle_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def handle_no(self) -> None:
        self.dismiss(False)


class DependencyScreen(Screen[bool]):
    """Check for ffmpeg and offer to install it if missing."""

    DEFAULT_CSS = """
    DependencyScreen {
        align: center middle;
    }
    #dep-box {
        width: 70;
        height: auto;
        border: solid $accent;
        padding: 1 2;
        background: $surface;
    }
    #dep-status {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        color: $foreground;
    }
    #dep-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #dep-buttons Button {
        margin: 0 2;
        border: none;
        min-width: 16;
        text-style: bold;
    }
    #dep-buttons #install {
        background: $success 20%;
        color: $success;
    }
    #dep-buttons #install:hover {
        background: $success 35%;
    }
    #dep-buttons #quit {
        background: $error 20%;
        color: $error;
    }
    #dep-buttons #quit:hover {
        background: $error 35%;
    }
    #dep-log {
        height: 14;
        border: solid $panel;
        margin-top: 1;
        display: none;
        background: $background;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dep-box"):
            yield Static("Checking for ffmpeg...", id="dep-status")
            yield RichLog(id="dep-log", highlight=True, markup=True)
            with Horizontal(id="dep-buttons"):
                yield Button("Install ffmpeg", id="install", variant="success")
                yield Button("Quit", id="quit", variant="error")

    def on_mount(self) -> None:
        self.query_one("#install", Button).display = False
        self.query_one("#quit", Button).display = False
        self.check_ffmpeg()

    @work(thread=True)
    def check_ffmpeg(self) -> None:
        if shutil.which("ffmpeg"):
            self.app.call_from_thread(self._ffmpeg_found)
        else:
            self.app.call_from_thread(self._ffmpeg_missing)

    def _ffmpeg_found(self) -> None:
        self._dismiss_success("[$success]ffmpeg found![/$success] Launching...")

    def _dismiss_success(self, message: str) -> None:
        self.query_one("#dep-status", Static).update(message)
        self.query_one("#install", Button).display = False
        self.query_one("#quit", Button).display = False
        self.set_timer(0.8, lambda: self.dismiss(True))

    def _ffmpeg_missing(self) -> None:
        system = platform.system()
        if system == "Darwin":
            brew = find_brew()
            if brew:
                msg = "[$error]ffmpeg not found.[/$error]\n\nInstall via Homebrew?"
            else:
                msg = (
                    "[$error]ffmpeg not found.[/$error]\n\n"
                    "Homebrew is also not installed.\n"
                    "We'll install Homebrew first, then ffmpeg."
                )
        elif system == "Linux":
            msg = "[$error]ffmpeg not found.[/$error]\n\nInstall via apt?"
        else:
            msg = (
                "[$error]ffmpeg not found.[/$error]\n\n"
                "Please install ffmpeg manually and re-run this app."
            )
        self.query_one("#dep-status", Static).update(msg)
        self.query_one("#install", Button).display = True
        self.query_one("#quit", Button).display = True
        if system not in ("Darwin", "Linux"):
            self.query_one("#install", Button).display = False

    @on(Button.Pressed, "#quit")
    def handle_quit(self) -> None:
        self.app.exit()

    @on(Button.Pressed, "#install")
    def handle_install(self) -> None:
        self.query_one("#install", Button).disabled = True
        self.query_one("#quit", Button).disabled = True
        self.query_one("#dep-status", Static).update("Installing... (the app will pause to use your terminal)")
        self.set_timer(0.5, self._run_install)

    def _run_install(self) -> None:
        system = platform.system()
        if system == "Darwin":
            self._install_macos()
        elif system == "Linux":
            self._install_linux()

    def _run_in_terminal(self, banner: str, cmd: list[str]) -> None:
        with self.app.suspend():
            print(f"\n--- {banner} ---\n")
            subprocess.run(cmd)
            print("\nPress Enter to continue...")
            input()

    def _install_macos(self) -> None:
        brew = find_brew()
        if not brew:
            self._run_in_terminal(
                "Installing Homebrew",
                ["/bin/bash", "-c", 'curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash'],
            )
            brew = find_brew()
            if not brew:
                self.query_one("#dep-status", Static).update(
                    "[$error]Homebrew installation failed or not found in PATH.[/$error]\n"
                    "Please install Homebrew manually and re-run."
                )
                self.query_one("#quit", Button).disabled = False
                return

        self._run_in_terminal("Installing ffmpeg via Homebrew", [brew, "install", "ffmpeg"])
        self._verify_install()

    def _install_linux(self) -> None:
        self._run_in_terminal(
            "Installing ffmpeg",
            ["sudo", "apt-get", "update"],
        )
        self._run_in_terminal(
            "Installing ffmpeg (apt-get install)",
            ["sudo", "apt-get", "install", "-y", "ffmpeg"],
        )
        self._verify_install()

    def _verify_install(self) -> None:
        if shutil.which("ffmpeg"):
            self._dismiss_success("[$success]ffmpeg installed successfully![/$success] Launching...")
        else:
            self.query_one("#dep-status", Static).update(
                "[$error]ffmpeg still not found after installation.[/$error]\n"
                "You may need to restart your terminal or add it to PATH."
            )
            self.query_one("#quit", Button).disabled = False


class FileBrowserScreen(Screen[str | None]):
    """A file browser using DirectoryTree."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    FileBrowserScreen {
        align: center middle;
    }
    #browser-box {
        width: 80;
        height: 30;
        border: solid $accent;
        padding: 1 2;
        background: $surface;
    }
    #browser-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $secondary;
    }
    #tree {
        height: 1fr;
        border: solid $panel;
        background: $background;
    }
    #selected-label {
        margin-top: 1;
        height: 1;
        color: $success;
    }
    #browser-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #browser-buttons Button {
        margin: 0 2;
        border: none;
        min-width: 16;
        height: 3;
        text-style: bold;
    }
    #browser-buttons #select {
        background: $primary 25%;
        color: $primary;
    }
    #browser-buttons #select:hover {
        background: $primary 40%;
    }
    #browser-buttons #cancel {
        background: $panel;
        color: $foreground 70%;
    }
    #browser-buttons #cancel:hover {
        background: $panel;
        color: $foreground;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_path: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="browser-box"):
            yield Static("Browse for a video file", id="browser-title")
            yield DirectoryTree(str(Path.home()), id="tree")
            yield Static("", id="selected-label")
            with Horizontal(id="browser-buttons"):
                yield Button("Select", id="select", variant="primary", disabled=True)
                yield Button("Cancel", id="cancel", variant="default")

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.selected_path = str(event.path)
        self.query_one("#selected-label", Static).update(f"Selected: {event.path.name}")
        self.query_one("#select", Button).disabled = False

    @on(Button.Pressed, "#select")
    def handle_select(self) -> None:
        if self.selected_path:
            self.dismiss(self.selected_path)

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class MainScreen(Screen):
    """Main screen — select a video and strip its metadata."""

    DEFAULT_CSS = """
    MainScreen {
        align: center middle;
    }
    #main-box {
        width: 80;
        height: auto;
        border: none;
        padding: 1 2;
        background: $surface;
    }
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #drop-zone {
        width: 100%;
        height: 9;
        border: none;
        padding: 1 2;
        margin-bottom: 1;
        background: $background;
    }
    #drop-zone:focus-within {
        border: none;
    }
    #drop-zone.has-file {
        border: solid $success;
        background: $success 8%;
    }
    #drop-zone.processing {
        border: solid $warning;
        background: $warning 8%;
    }
    #drop-hint {
        text-align: center;
        color: $secondary 60%;
        width: 100%;
        margin-bottom: 2;
    }
    #drop-filename {
        text-align: center;
        text-style: bold;
        color: $success;
        width: 100%;
        display: none;
    }
    #file-path {
        width: 100%;
        background: transparent;
        color: $foreground;
        border: none;
    }
    #file-path:focus {
        border: none;
    }
    #secondary-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #secondary-row Button {
        margin: 0 1;
        border: none;
        min-width: 20;
        height: 3;
        text-style: bold;
    }
    #secondary-row #browse {
        background: $panel;
        color: $secondary;
    }
    #secondary-row #browse:hover {
        background: $secondary 20%;
    }
    #secondary-row #strip {
        background: $primary 25%;
        color: $primary;
    }
    #secondary-row #strip:hover {
        background: $primary 40%;
    }
    #status {
        text-align: center;
        margin-top: 1;
        height: auto;
        min-height: 1;
        color: $foreground;
    }
    #progress {
        margin-top: 1;
        display: none;
    }
    #log {
        height: 10;
        border: solid $panel;
        background: $background;
        margin-top: 1;
        display: none;
    }
    #quit-btn {
        dock: top;
        width: auto;
        min-width: 10;
        height: 3;
        margin: 1 2;
        background: $success 15%;
        color: $success;
        border: none;
        text-style: bold;
    }
    #quit-btn:hover {
        background: $success 30%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="main-box"):
            yield Static("METADATA REMOVER", id="title")
            with Vertical(id="drop-zone"):
                yield Static(
                    "Drag & drop a video file here",
                    id="drop-hint",
                )
                yield Static("", id="drop-filename")
                yield Input(
                    placeholder="or type / paste a file path...",
                    id="file-path",
                )
            with Horizontal(id="secondary-row"):
                yield Button("Browse", id="browse", variant="default")
                yield Button("Strip Metadata", id="strip", variant="primary")
            yield Static("", id="status")
            yield ProgressBar(id="progress", total=None, show_eta=False)
            yield RichLog(id="log", highlight=True, markup=True)
        yield Button("Quit", id="quit-btn")
        yield GridBackground()

    def _clean_path(self, raw: str) -> str:
        """Strip surrounding quotes and trailing whitespace from pasted paths."""
        cleaned = raw.strip()
        if (cleaned.startswith("'") and cleaned.endswith("'")) or (
            cleaned.startswith('"') and cleaned.endswith('"')
        ):
            cleaned = cleaned[1:-1]
        return cleaned

    @on(Input.Changed, "#file-path")
    def on_path_changed(self, event: Input.Changed) -> None:
        """Auto-detect a valid video file and start stripping immediately."""
        raw = event.value
        path_str = self._clean_path(raw)
        drop_zone = self.query_one("#drop-zone")
        hint = self.query_one("#drop-hint", Static)
        filename_label = self.query_one("#drop-filename", Static)

        if not path_str:
            drop_zone.remove_class("has-file")
            hint.display = True
            filename_label.display = False
            return

        result = validate_video_file(path_str)
        if isinstance(result, Path):
            drop_zone.add_class("has-file")
            hint.display = False
            filename_label.update(f"{result.name}")
            filename_label.display = True
            if path_str != raw:
                self.query_one("#file-path", Input).value = path_str
                return  # the normalised change will re-trigger this handler
            self._start_strip(result)

    @on(Button.Pressed, "#quit-btn")
    def handle_quit(self) -> None:
        self.app.exit()

    @on(Button.Pressed, "#browse")
    def handle_browse(self) -> None:
        self.action_browse()

    def action_browse(self) -> None:
        def on_file_chosen(path: str | None) -> None:
            if path:
                self.query_one("#file-path", Input).value = path

        self.app.push_screen(FileBrowserScreen(), callback=on_file_chosen)

    @on(Button.Pressed, "#strip")
    def handle_strip(self) -> None:
        path_str = self._clean_path(self.query_one("#file-path", Input).value)
        result = validate_video_file(path_str)
        if isinstance(result, str):
            self.query_one("#status", Static).update(f"[$error]{result}[/$error]")
            return
        self._start_strip(result)

    def _start_strip(self, resolved_path: Path) -> None:
        self._set_controls_disabled(True)
        self.query_one("#status", Static).update("[$warning]Stripping metadata...[/$warning]")
        self.query_one("#progress", ProgressBar).display = True
        log = self.query_one("#log", RichLog)
        log.display = True
        log.clear()
        self.strip_metadata(resolved_path)

    @work(thread=True)
    def strip_metadata(self, input_path: Path) -> None:
        output_path = get_output_path(input_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c", "copy",
            str(output_path),
        ]

        log = self.query_one("#log", RichLog)
        self.app.call_from_thread(log.write, f"[dim]$ {' '.join(cmd)}[/dim]")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in process.stdout:  # type: ignore[union-attr]
                self.app.call_from_thread(log.write, line.rstrip())
            process.wait()
        except FileNotFoundError:
            self.app.call_from_thread(self._on_strip_done, "[$error]Error: ffmpeg not found in PATH.[/$error]")
            return
        except Exception as exc:
            self.app.call_from_thread(self._on_strip_done, f"[$error]Error: {exc}[/$error]")
            return

        if process.returncode == 0:
            self.app.call_from_thread(
                self._on_strip_done,
                f"[$success]Done![/$success] Saved to:\n{output_path}",
            )
        else:
            if output_path.exists():
                output_path.unlink()
            self.app.call_from_thread(
                self._on_strip_done,
                f"[$error]Error: ffmpeg exited with code {process.returncode}[/$error]",
            )

    def _on_strip_done(self, message: str) -> None:
        self.query_one("#status", Static).update(message)
        self.query_one("#progress", ProgressBar).display = False
        self._set_controls_disabled(False)

    def _set_controls_disabled(self, disabled: bool) -> None:
        for sel, cls in (("#strip", Button), ("#browse", Button), ("#file-path", Input)):
            self.query_one(sel, cls).disabled = disabled
        drop_zone = self.query_one("#drop-zone")
        if disabled:
            drop_zone.add_class("processing")
        else:
            drop_zone.remove_class("processing")


class MetadataRemoverApp(App):
    """A TUI application to strip metadata from video files."""

    TITLE = "Metadata Remover"
    CSS = """
    Screen {
        background: $background;
        layers: below default;
    }
    ProgressBar Bar > .bar--bar {
        color: $primary;
    }
    ProgressBar Bar > .bar--indeterminate {
        color: $secondary;
    }
    """

    def on_mount(self) -> None:
        self.register_theme(CYBER_THEME)
        self.theme = "cyberpunk"

        def on_dep_check(result: bool) -> None:
            if result:
                self.push_screen(MainScreen())

        self.push_screen(DependencyScreen(), callback=on_dep_check)



if __name__ == "__main__":
    MetadataRemoverApp().run()
