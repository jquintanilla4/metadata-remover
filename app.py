"""Metadata Remover — strip metadata from video files using ffmpeg."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path

import webview

# ─── Constants ───────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
}


# ─── Utility functions ───────────────────────────────────────────

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


def find_ffmpeg() -> str | None:
    """Return the path to ffmpeg, checking common locations."""
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


# ─── HTML ────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Metadata Remover</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0d1017;
    color: #bfbdb6;
    font-family: 'DM Sans', -apple-system, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 40px 20px;
    overflow-y: auto;
  }

  #container {
    width: 100%;
    max-width: 520px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* ---- Header / Title ---- */
  #header {
    text-align: center;
    padding: 0 0 4px 0;
  }
  #title {
    font-size: 32px;
    font-weight: 700;
    color: #bfbdb6;
    letter-spacing: -0.5px;
  }
  #title span { color: #e6b450; }
  #subtitle {
    margin-top: 6px;
    font-size: 13px;
    font-weight: 300;
    color: #565b66;
  }

  /* ---- Dependency Overlay ---- */
  #dep-overlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(13, 16, 23, 0.96);
    justify-content: center;
    align-items: center;
  }
  #dep-overlay.visible { display: flex; }
  #dep-box {
    background: #131620;
    border: 1px solid #1a1e2a;
    border-radius: 10px;
    padding: 28px 32px;
    text-align: center;
    max-width: 420px;
    width: 90%;
  }
  #dep-status { margin-bottom: 16px; line-height: 1.6; font-size: 14px; }
  #dep-buttons { display: none; justify-content: center; gap: 12px; }
  #dep-log {
    display: none;
    margin-top: 16px;
    background: #0d1017;
    border: 1px solid #1a1e2a;
    border-radius: 8px;
    padding: 10px 12px;
    max-height: 180px;
    overflow-y: auto;
    text-align: left;
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    font-size: 11px;
    white-space: pre-wrap;
    color: #565b66;
  }

  /* ---- Controls ---- */
  #controls {
    background: #131620;
    border: 1px solid #1a1e2a;
    border-radius: 10px;
    padding: 20px 22px;
  }
  #input-label {
    font-size: 11px;
    font-weight: 500;
    color: #565b66;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
  }
  #file-path {
    width: 100%;
    padding: 11px 14px;
    background: #0d1017;
    color: #bfbdb6;
    border: 1px solid #1a1e2a;
    border-radius: 8px;
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
  }
  #file-path:focus { border-color: #e6b450; }
  #file-path::placeholder { color: #3d424d; }
  #file-path:disabled { opacity: 0.4; }

  #button-row {
    display: flex;
    gap: 10px;
    margin-top: 14px;
  }

  /* ---- Buttons ---- */
  button {
    padding: 9px 20px;
    border: none;
    border-radius: 8px;
    font-family: 'DM Sans', -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
  }
  button:active:not(:disabled) { transform: scale(0.97); }
  button:disabled { opacity: 0.35; cursor: not-allowed; }

  .btn-browse { background: #1a1e2a; color: #8b919d; flex: 1; }
  .btn-browse:hover:not(:disabled) { background: #212535; color: #bfbdb6; }
  .btn-strip { background: #e6b450; color: #0d1017; flex: 1; }
  .btn-strip:hover:not(:disabled) { background: #d4a43e; }
  .btn-reset { background: #1a1e2a; color: #8b919d; display: none; }
  .btn-reset:hover:not(:disabled) { background: #212535; color: #bfbdb6; }
  .btn-install { background: #aad94c; color: #0d1017; }
  .btn-install:hover:not(:disabled) { background: #99c83e; }
  .btn-quit { background: #1a1e2a; color: #565b66; }
  .btn-quit:hover:not(:disabled) { background: #212535; color: #bfbdb6; }

  /* ---- Status ---- */
  #status {
    text-align: center;
    margin-top: 12px;
    min-height: 18px;
    line-height: 1.5;
    font-size: 13px;
  }
  .status-success { color: #aad94c; }
  .status-error { color: #f07178; }
  .status-warning { color: #e6b450; }

  /* ---- Progress ---- */
  #progress-bar {
    display: none;
    margin-top: 12px;
    height: 3px;
    background: #1a1e2a;
    border-radius: 2px;
    overflow: hidden;
  }
  #progress-bar .indeterminate {
    width: 30%;
    height: 100%;
    background: #e6b450;
    border-radius: 2px;
    animation: slide 1.6s ease-in-out infinite;
  }
  @keyframes slide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(430%); }
  }

  /* ---- Drop Zone ---- */
  #drop-zone {
    border: 1px dashed #252a38;
    border-radius: 10px;
    padding: 32px 16px;
    text-align: center;
    transition: border-color 0.25s, background 0.25s;
    cursor: default;
  }
  #drop-zone.drag-over {
    border: 2px dashed #e6b450;
    background: rgba(230, 180, 80, 0.07);
  }
  #drop-zone.has-file {
    border-color: #aad94c;
    border-style: solid;
    background: rgba(170, 217, 76, 0.04);
  }
  #drop-zone.processing {
    border-color: #e6b450;
    border-style: solid;
    background: rgba(230, 180, 80, 0.04);
  }
  #drop-label { color: #3d424d; font-size: 13px; font-weight: 500; }
  #drop-filename {
    display: none;
    color: #aad94c;
    font-weight: 600;
    word-break: break-all;
    font-size: 13px;
  }

  /* ---- Output ---- */
  #output-section {
    display: none;
    background: #080b12;
    border: 1px solid #1a1e2a;
    border-radius: 10px;
    max-height: 240px;
    overflow: hidden;
  }
  #output-log {
    padding: 14px 16px;
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    font-size: 11px;
    line-height: 1.7;
    overflow-y: auto;
    max-height: 236px;
    white-space: pre-wrap;
    word-break: break-all;
    color: #565b66;
  }
  .log-cmd { color: #3d424d; }
  .log-line { color: #565b66; }
</style>
</head>
<body>

<!-- Dependency overlay -->
<div id="dep-overlay">
  <div id="dep-box">
    <div id="dep-status">Checking for ffmpeg...</div>
    <div id="dep-log"></div>
    <div id="dep-buttons">
      <button class="btn-install" id="btn-install" onclick="installFfmpeg()">Install ffmpeg</button>
      <button class="btn-quit" id="btn-quit-dep" onclick="quitApp()">Quit</button>
    </div>
  </div>
</div>

<div id="container">
  <!-- Header -->
  <div id="header">
    <div id="title">Metadata<span>.</span>Remover</div>
    <div id="subtitle">Strip metadata from video files</div>
  </div>

  <!-- Controls -->
  <div id="controls">
    <div id="input-label">File path</div>
    <input type="text" id="file-path" placeholder="Paste a file path..." autocomplete="off" spellcheck="false">
    <div id="button-row">
      <button class="btn-reset" id="btn-reset" onclick="newSession()">New Session</button>
      <button class="btn-browse" id="btn-browse" onclick="browseFile()">Browse</button>
      <button class="btn-strip" id="btn-strip" onclick="stripMetadata()">Strip Metadata</button>
    </div>
    <div id="status"></div>
    <div id="progress-bar"><div class="indeterminate"></div></div>
  </div>

  <!-- Drop zone -->
  <div id="drop-zone">
    <div id="drop-label">drag & drop video file here</div>
    <div id="drop-filename"></div>
  </div>

  <!-- Section 3: Output log (hidden until processing) -->
  <div id="output-section">
    <div id="output-log"></div>
  </div>
</div>

<script>
// ---- State ----
let processing = false;

// ---- DOM refs ----
const dropZone      = document.getElementById('drop-zone');
const dropLabel     = document.getElementById('drop-label');
const dropFilename  = document.getElementById('drop-filename');
const filePathInput = document.getElementById('file-path');
const btnBrowse     = document.getElementById('btn-browse');
const btnStrip      = document.getElementById('btn-strip');
const btnReset      = document.getElementById('btn-reset');
const statusEl      = document.getElementById('status');
const progressBar   = document.getElementById('progress-bar');
const outputSection = document.getElementById('output-section');
const outputLog     = document.getElementById('output-log');
const depOverlay    = document.getElementById('dep-overlay');
const depStatus     = document.getElementById('dep-status');
const depButtons    = document.getElementById('dep-buttons');
const depLog        = document.getElementById('dep-log');

// ---- Startup: check ffmpeg ----
window.addEventListener('pywebviewready', function() {
    depOverlay.classList.add('visible');
    pywebview.api.check_ffmpeg().then(function(result) {
        if (result.found) {
            depStatus.innerHTML = '<span class="status-success">ffmpeg found!</span> Launching...';
            setTimeout(function() { depOverlay.classList.remove('visible'); }, 800);
        } else {
            depStatus.innerHTML = result.message;
            depButtons.style.display = 'flex';
            if (!result.can_install) {
                document.getElementById('btn-install').style.display = 'none';
            }
        }
    });
});

// ---- Dependency install ----
function installFfmpeg() {
    document.getElementById('btn-install').disabled = true;
    document.getElementById('btn-quit-dep').disabled = true;
    depStatus.textContent = 'Installing ffmpeg... this may take a few minutes.';
    depLog.style.display = 'block';
    pywebview.api.install_ffmpeg().then(function(result) {
        if (result.success) {
            depStatus.innerHTML = '<span class="status-success">ffmpeg installed!</span> Launching...';
            depButtons.style.display = 'none';
            setTimeout(function() { depOverlay.classList.remove('visible'); }, 800);
        } else {
            depStatus.innerHTML = '<span class="status-error">' + result.message + '</span>';
            document.getElementById('btn-quit-dep').disabled = false;
        }
    });
}

function quitApp() {
    pywebview.api.quit_app();
}

// ---- Browse ----
function browseFile() {
    if (processing) return;
    pywebview.api.browse_file().then(function(path) {
        if (path) {
            filePathInput.value = path;
            onPathChanged(path);
        }
    });
}

// ---- Strip metadata (manual button) ----
function stripMetadata() {
    var path = filePathInput.value.trim();
    if (!path || processing) return;
    pywebview.api.validate_and_strip(path);
}

// ---- Input change with debounce ----
var debounceTimer = null;
filePathInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function() {
        onPathChanged(filePathInput.value.trim());
    }, 300);
});

function onPathChanged(path) {
    if (!path) {
        dropZone.className = '';
        dropLabel.style.display = '';
        dropFilename.style.display = 'none';
        return;
    }
    pywebview.api.validate_and_strip(path);
}

// ---- Drag & drop visual feedback (JS-only, Python handles actual drop) ----
var dragCounter = 0;
dropZone.addEventListener('dragenter', function(e) { e.preventDefault(); dragCounter++; dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', function(e) { e.preventDefault(); dragCounter--; if (dragCounter <= 0) { dragCounter = 0; dropZone.classList.remove('drag-over'); } });
dropZone.addEventListener('dragover', function(e) { e.preventDefault(); });
dropZone.addEventListener('drop', function(e) { e.preventDefault(); dragCounter = 0; dropZone.classList.remove('drag-over'); });

// Also handle drops on the whole document so files dragged anywhere work
document.addEventListener('dragover', function(e) { e.preventDefault(); });
document.addEventListener('drop', function(e) { e.preventDefault(); });

// ---- Functions called from Python via evaluate_js ----

function setDropFile(filename) {
    dropLabel.style.display = 'none';
    dropFilename.style.display = '';
    dropFilename.textContent = filename;
    dropZone.className = 'has-file';
}

function setProcessing(isProcessing) {
    processing = isProcessing;
    btnBrowse.disabled = isProcessing;
    btnStrip.disabled = isProcessing;
    filePathInput.disabled = isProcessing;
    progressBar.style.display = isProcessing ? 'block' : 'none';
    if (isProcessing) {
        btnReset.style.display = 'none';
        dropZone.classList.add('processing');
        dropZone.classList.remove('has-file');
        outputSection.style.display = 'block';
        outputLog.innerHTML = '';
    } else {
        btnReset.style.display = 'inline-block';
        dropZone.classList.remove('processing');
        dropZone.classList.remove('has-file');
        dropLabel.style.display = '';
        dropFilename.style.display = 'none';
    }
}

function setStatus(html, cls) {
    statusEl.innerHTML = html;
    statusEl.className = cls || '';
}

function appendLog(text, cls) {
    var line = document.createElement('div');
    line.className = cls || 'log-line';
    line.textContent = text;
    outputLog.appendChild(line);
    outputLog.scrollTop = outputLog.scrollHeight;
}

function setFilePath(path) {
    filePathInput.value = path;
}

function newSession() {
    processing = false;
    filePathInput.value = '';
    filePathInput.disabled = false;
    btnBrowse.disabled = false;
    btnStrip.disabled = false;
    btnReset.style.display = 'none';
    statusEl.innerHTML = '';
    statusEl.className = '';
    progressBar.style.display = 'none';
    outputSection.style.display = 'none';
    outputLog.innerHTML = '';
    dropZone.className = '';
    dropLabel.style.display = '';
    dropFilename.style.display = 'none';
}

function appendDepLog(text) {
    depLog.textContent += text + '\\n';
    depLog.scrollTop = depLog.scrollHeight;
}
</script>
</body>
</html>"""


# ─── Api class ───────────────────────────────────────────────────

class Api:
    """Exposed to JavaScript via js_api. Methods run in background threads."""

    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._lock = threading.Lock()

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    # ---- Dependency checking ----

    def check_ffmpeg(self) -> dict:
        if find_ffmpeg():
            return {"found": True, "message": "", "can_install": False}

        system = platform.system()
        if system == "Darwin":
            brew = find_brew()
            if brew:
                msg = '<span class="status-error">ffmpeg not found.</span><br><br>Install via Homebrew?'
            else:
                msg = (
                    '<span class="status-error">ffmpeg not found.</span><br><br>'
                    "Homebrew is also not installed.<br>"
                    "We'll install Homebrew first, then ffmpeg."
                )
            return {"found": False, "message": msg, "can_install": True}
        elif system == "Linux":
            return {
                "found": False,
                "message": '<span class="status-error">ffmpeg not found.</span><br><br>Install via apt?',
                "can_install": True,
            }
        else:
            return {
                "found": False,
                "message": (
                    '<span class="status-error">ffmpeg not found.</span><br><br>'
                    "Please install ffmpeg manually and re-run."
                ),
                "can_install": False,
            }

    def install_ffmpeg(self) -> dict:
        system = platform.system()
        try:
            if system == "Darwin":
                brew = find_brew()
                if not brew:
                    self._run_and_stream(
                        ["/bin/bash", "-c",
                         "curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash"],
                        log_target="dep",
                    )
                    brew = find_brew()
                    if not brew:
                        return {"success": False, "message": "Homebrew installation failed."}
                self._run_and_stream([brew, "install", "ffmpeg"], log_target="dep")
            elif system == "Linux":
                self._run_and_stream(["sudo", "apt-get", "update"], log_target="dep")
                self._run_and_stream(["sudo", "apt-get", "install", "-y", "ffmpeg"], log_target="dep")

            if find_ffmpeg():
                return {"success": True, "message": ""}
            else:
                return {"success": False, "message": "ffmpeg still not found after installation."}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def quit_app(self) -> None:
        if self._window:
            self._window.destroy()

    # ---- File browsing ----

    def browse_file(self) -> str | None:
        if not self._window:
            return None
        extensions = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        file_types = (f"Video Files ({extensions})",)
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=file_types,
        )
        if result and len(result) > 0:
            return result[0]
        return None

    # ---- Validation + strip ----

    def validate_and_strip(self, path_str: str) -> None:
        path_str = self._clean_path(path_str)
        result = validate_video_file(path_str)

        if isinstance(result, str):
            self._eval(f"setStatus({self._js(result)}, 'status-error')")
            return

        self._eval(f"setDropFile({self._js(result.name)})")
        self._eval(f"setFilePath({self._js(str(result))})")

        if not self._lock.acquire(blocking=False):
            return  # already processing
        try:
            self._strip_metadata(result)
        finally:
            self._lock.release()

    # ---- Core strip logic ----

    def _strip_metadata(self, input_path: Path) -> None:
        self._eval("setProcessing(true)")
        self._eval("setStatus('Stripping metadata...', 'status-warning')")

        output_path = get_output_path(input_path)
        ffmpeg_bin = find_ffmpeg() or "ffmpeg"
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_path),
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c", "copy",
            str(output_path),
        ]

        self._eval(f"appendLog({self._js('$ ' + ' '.join(cmd))}, 'log-cmd')")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in process.stdout:  # type: ignore[union-attr]
                self._eval(f"appendLog({self._js(line.rstrip())}, 'log-line')")
            process.wait()
        except FileNotFoundError:
            self._eval("setProcessing(false)")
            self._eval("setStatus('Error: ffmpeg not found in PATH.', 'status-error')")
            return
        except Exception as exc:
            self._eval("setProcessing(false)")
            self._eval(f"setStatus({self._js(f'Error: {exc}')}, 'status-error')")
            return

        self._eval("setProcessing(false)")
        if process.returncode == 0:
            msg = f"Done! Saved to:<br>{output_path}"
            self._eval(f"setStatus({self._js(msg)}, 'status-success')")
        else:
            if output_path.exists():
                output_path.unlink()
            self._eval(
                f"setStatus('Error: ffmpeg exited with code {process.returncode}', 'status-error')"
            )

    # ---- Helpers ----

    def _run_and_stream(self, cmd: list[str], log_target: str = "output") -> None:
        append_fn = "appendDepLog" if log_target == "dep" else "appendLog"
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        for line in process.stdout:  # type: ignore[union-attr]
            self._eval(f"{append_fn}({self._js(line.rstrip())})")
        process.wait()

    def _eval(self, js_code: str) -> None:
        if self._window:
            self._window.evaluate_js(js_code)

    @staticmethod
    def _clean_path(raw: str) -> str:
        cleaned = raw.strip()
        if (cleaned.startswith("'") and cleaned.endswith("'")) or \
           (cleaned.startswith('"') and cleaned.endswith('"')):
            cleaned = cleaned[1:-1]
        return cleaned

    @staticmethod
    def _js(s: str) -> str:
        """Escape a Python string for safe embedding in JS."""
        return json.dumps(s)


# ─── Drag & drop (Python-side for pywebviewFullPath) ─────────────

def _on_drop(e: dict) -> None:
    files = e.get("dataTransfer", {}).get("files", [])
    if not files:
        return
    full_path = files[0].get("pywebviewFullPath")
    if full_path:
        api.validate_and_strip(full_path)


def _on_drag(e: dict) -> None:
    pass  # preventDefault handled by DOMEventHandler flags


def _bind_events(window: webview.Window) -> None:
    from webview.dom import DOMEventHandler
    window.dom.document.events.dragenter += DOMEventHandler(_on_drag, True, True)
    window.dom.document.events.dragover += DOMEventHandler(_on_drag, True, True)
    window.dom.document.events.drop += DOMEventHandler(_on_drop, True, True)


# ─── Entry point ─────────────────────────────────────────────────

api = Api()

if __name__ == "__main__":
    window = webview.create_window(
        title="Metadata Remover",
        html=HTML,
        js_api=api,
        width=720,
        height=820,
        resizable=True,
        background_color="#0d1017",
        text_select=False,
        min_size=(480, 600),
    )
    api.set_window(window)
    window.events.loaded += _bind_events
    webview.start(debug=False)
