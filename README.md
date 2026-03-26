# Metadata Remover

Metadata Remover is a desktop app that removes metadata from video files without re-encoding the video. It is built with Electron and uses the `ffmpeg` already installed on the user's machine.

The current app is macOS-first. It includes a guided setup flow for `ffmpeg` and Homebrew so the app can help users get ready before they process a file.

## What The App Does

- Drag and drop a video file to start processing right away
- Browse for a file with the native file picker
- Paste a file path manually
- Check that the file exists, is supported, and can be written back out safely
- Show the exact `ffmpeg` command and live output in the app
- Save the cleaned file next to the original
- Automatically avoid filename collisions with `_clean`, `_clean_1`, `_clean_2`, and so on

## How It Works

When you provide a video file, the app runs:

```bash
ffmpeg -y -i input.mp4 -map_metadata -1 -map_chapters -1 -c copy output_clean.mp4
```

- `-map_metadata -1` removes metadata
- `-map_chapters -1` removes chapter markers
- `-c copy` keeps the original audio and video streams without re-encoding

Because the file is copied instead of re-encoded, processing is usually fast and does not reduce video quality.

## Supported Formats

`.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.3gp` `.ts`

## ffmpeg Setup In The App

On startup, the app checks for `ffmpeg` in:

- your `PATH`
- `/opt/homebrew/bin/ffmpeg`
- `/usr/local/bin/ffmpeg`

If `ffmpeg` is missing:

- and Homebrew is already installed, the app offers an in-app `Install ffmpeg` button
- and Homebrew is not installed yet, the app shows the Homebrew install command, lets the user copy it, and links to the official Homebrew website

## Run The App For Development

Install dependencies:

```bash
npm install
```

Start the Electron app:

```bash
make run
```

Type-check the project:

```bash
make typecheck
```

## Build The App

This section is written for non-technical users.

Building the app means creating a version you can open like a normal desktop app instead of running it from source code.

1. Open the Terminal app on your Mac.
2. Go to this project folder.
3. Install the project tools:

```bash
npm install
```

4. Create the packaged app:

```bash
make build
```

After `make build` finishes, look in the `out/` folder. That folder will contain a packaged copy of the app.

If you want installable/shareable Mac files such as a `.dmg` and `.zip`, run:

```bash
make app
```

After `make app` finishes, look in `out/make/`.

You should find:

- a `.dmg` file you can open and install like a normal Mac app
- a `.zip` file you can send to someone else or keep as a packaged build

### Build Commands At A Glance

- `make build`: creates a packaged app in `out/`
- `make app`: creates Mac distributables in `out/make/`
- `make run`: launches the app for local development
- `make typecheck`: checks TypeScript for type errors

## Project Structure

```text
src/main.ts             Electron main process and ffmpeg/Homebrew integration
src/preload.ts          Secure renderer bridge
src/App.tsx             React UI
src/styles.css          App styles
src/shared/constants.ts Shared app constants
src/shared/types.ts     Shared TypeScript types
forge.config.ts         Electron Forge packaging config
webpack.*.ts            Webpack configuration used by Forge
package.json            Project scripts and dependencies
Makefile                Shortcut commands for running and building
```

## License

MIT
