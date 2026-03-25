# Metadata Remover

A macOS-first Electron desktop app that strips metadata from video files with the user's installed `ffmpeg`.

## Features

- Drag and drop a video file into the app
- Browse for a file with the native macOS file picker
- Paste a file path manually
- Stream `ffmpeg` output live in the UI
- Save the cleaned copy next to the original with a `_clean` suffix

## How It Works

When you provide a video file, the app runs:

```bash
ffmpeg -y -i input.mp4 -map_metadata -1 -map_chapters -1 -c copy output_clean.mp4
```

- `-map_metadata -1` removes global, stream, and chapter metadata
- `-map_chapters -1` removes chapter markers
- `-c copy` copies streams without re-encoding

If `output_clean.ext` already exists, the app writes `output_clean_1.ext`, `output_clean_2.ext`, and so on.

## Supported Formats

`.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.3gp` `.ts`

## ffmpeg Dependency Flow

The app uses the user's local `ffmpeg`.

On startup it checks:

- `PATH`
- `/opt/homebrew/bin/ffmpeg`
- `/usr/local/bin/ffmpeg`

If `ffmpeg` is missing on macOS:

- If Homebrew exists, the app offers a one-click `brew install ffmpeg`
- If Homebrew is missing, the app shows the official Homebrew install command and link, then asks the user to retry after Homebrew is installed

## Development

Install dependencies:

```bash
npm install
```

Run the Electron app:

```bash
make run
```

Typecheck:

```bash
make typecheck
```

## Packaging

Package the app:

```bash
make build
```

This runs `npm run package` and writes the packaged app under `out/`.

Make macOS distributables:

```bash
make app
```

This runs `npm run make` and writes distributables under `out/make`, including:

- a `.zip`
- a `.dmg`

## Project Structure

```text
src/main.ts             Electron main process
src/preload.ts          Secure preload bridge
src/App.tsx             React UI
src/styles.css          App styles
forge.config.ts         Electron Forge packaging config
webpack.*.ts            Webpack configuration used by Forge
package.json            Node/Electron project definition
```

## License

MIT
