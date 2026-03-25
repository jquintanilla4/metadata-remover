# Electron Rewrite Plan For Metadata Remover

## Summary

Replace the original desktop app with a macOS-first Electron app using Electron Forge, React, and TypeScript. Keep the existing product behavior: drag/drop or browse for a video, strip metadata with the same `ffmpeg` flags, stream logs live, and save a `_clean` output next to the source file.

Use the user's installed `ffmpeg`. If it is missing and Homebrew exists, offer a one-click `brew install ffmpeg`. If Homebrew is missing, do not auto-install it; show the official Homebrew install command and link instead.

## Key Changes

- Scaffold the app with Electron Forge and a React + TypeScript renderer
- Move filesystem access, dependency checks, dialogs, and subprocesses into the Electron main process
- Expose a narrow preload bridge to the renderer
- Preserve the current UI flow: dependency overlay, browse/paste/drag-and-drop, live logs, and new-session reset
- The legacy Python implementation has been removed and Electron is now the only app runtime in the repo

## Public Interfaces

The renderer talks to the main process through `window.metadataRemover`:

- `checkDependencies()`
- `browseFile()`
- `validatePath(path)`
- `stripMetadata(path)`
- `installFfmpeg()`
- `openExternal(url)`
- `copyText(text)`
- `quitApp()`
- `onStripEvent(callback)`
- `onInstallEvent(callback)`

## Test Cases

- Launch with `ffmpeg` installed
- Launch without `ffmpeg` but with Homebrew available
- Launch without Homebrew installed
- Drag/drop a supported file and verify immediate hover feedback
- Browse for a supported file
- Paste valid and invalid paths
- Run a strip job and verify live logs, output naming, and failure cleanup
- Build a packaged macOS app and verify ZIP/DMG generation

## Assumptions

- v1 targets macOS only
- The renderer uses React + TypeScript
- The app uses the user's installed `ffmpeg` and does not bundle it
- Homebrew itself is not auto-installed
