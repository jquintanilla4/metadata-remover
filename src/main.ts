declare const MAIN_WINDOW_WEBPACK_ENTRY: string;
declare const MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY: string;

import { accessSync, constants, existsSync, statSync, unlinkSync } from 'node:fs';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { spawn } from 'node:child_process';

import {
  app,
  BrowserWindow,
  clipboard,
  dialog,
  ipcMain,
  shell,
} from 'electron';

import {
  COMMON_BREW_PATHS,
  COMMON_FFMPEG_PATHS,
  HOMEBREW_INSTALL_COMMAND,
  HOMEBREW_URL,
  SUPPORTED_EXTENSIONS,
} from './shared/constants';
import type {
  CommandStartResult,
  DependencyCheckResult,
  InstallEvent,
  StatusLevel,
  StripEvent,
  ValidationResult,
} from './shared/types';

let mainWindow: BrowserWindow | null = null;
let stripProcess: ReturnType<typeof spawn> | null = null;
let installProcess: ReturnType<typeof spawn> | null = null;

const supportedExtensionSet = new Set<string>(SUPPORTED_EXTENSIONS);

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 720,
    height: 860,
    minWidth: 520,
    minHeight: 640,
    backgroundColor: '#0d1017',
    autoHideMenuBar: true,
    show: false,
    title: 'Metadata Remover',
    webPreferences: {
      preload: MAIN_WINDOW_PRELOAD_WEBPACK_ENTRY,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  void mainWindow.loadURL(MAIN_WINDOW_WEBPACK_ENTRY);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function emitStrip(event: StripEvent): void {
  mainWindow?.webContents.send('metadata:stripEvent', event);
}

function emitInstall(event: InstallEvent): void {
  mainWindow?.webContents.send('metadata:installEvent', event);
}

function updateStripStatus(level: StatusLevel, message: string): void {
  emitStrip({ type: 'status', level, message });
}

function updateInstallStatus(level: StatusLevel, message: string): void {
  emitInstall({ type: 'status', level, message });
}

function cleanPath(rawPath: string): string {
  const trimmed = rawPath.trim();

  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }

  return trimmed;
}

function resolveExecutable(name: string, candidates: string[]): string | null {
  const possiblePaths = new Set<string>();

  for (const dir of (process.env.PATH ?? '').split(path.delimiter)) {
    if (dir) {
      possiblePaths.add(path.join(dir, name));
    }
  }

  for (const candidate of candidates) {
    possiblePaths.add(candidate);
  }

  for (const candidate of possiblePaths) {
    try {
      accessSync(candidate, constants.X_OK);
      return candidate;
    } catch {
      continue;
    }
  }

  return null;
}

function findBrew(): string | null {
  return resolveExecutable('brew', COMMON_BREW_PATHS);
}

function findFfmpeg(): string | null {
  return resolveExecutable('ffmpeg', COMMON_FFMPEG_PATHS);
}

function getOutputPath(inputPath: string): string {
  const parsed = path.parse(inputPath);
  let attempt = path.join(parsed.dir, `${parsed.name}_clean${parsed.ext}`);
  let counter = 1;

  while (existsSync(attempt)) {
    attempt = path.join(parsed.dir, `${parsed.name}_clean_${counter}${parsed.ext}`);
    counter += 1;
  }

  return attempt;
}

function validateVideoFile(rawPath: string): ValidationResult {
  const cleaned = cleanPath(rawPath);

  if (!cleaned) {
    return { ok: false, message: 'No file path provided.' };
  }

  const resolvedPath = path.resolve(cleaned);

  if (!existsSync(resolvedPath)) {
    return { ok: false, message: `File not found: ${resolvedPath}` };
  }

  const stats = statSync(resolvedPath);

  if (!stats.isFile()) {
    return { ok: false, message: `Not a file: ${resolvedPath}` };
  }

  const extension = path.extname(resolvedPath).toLowerCase();

  if (!supportedExtensionSet.has(extension)) {
    return {
      ok: false,
      message: `Unsupported format '${extension}'. Supported: ${[...supportedExtensionSet].sort().join(', ')}`,
    };
  }

  try {
    accessSync(resolvedPath, constants.R_OK);
  } catch {
    return { ok: false, message: `Permission denied (cannot read): ${resolvedPath}` };
  }

  try {
    accessSync(path.dirname(resolvedPath), constants.W_OK);
  } catch {
    return {
      ok: false,
      message: `Permission denied (cannot write to directory): ${path.dirname(resolvedPath)}`,
    };
  }

  return {
    ok: true,
    resolvedPath,
    fileName: path.basename(resolvedPath),
  };
}

function checkDependencies(): DependencyCheckResult {
  const ffmpegPath = findFfmpeg();
  const brewPath = findBrew();

  if (ffmpegPath) {
    return {
      ffmpegFound: true,
      brewFound: Boolean(brewPath),
      installMode: 'ready',
      message: `ffmpeg found at ${ffmpegPath}`,
    };
  }

  if (brewPath) {
    return {
      ffmpegFound: false,
      brewFound: true,
      installMode: 'install-ffmpeg',
      message: 'ffmpeg is not installed. Install it with Homebrew to continue.',
      installCommand: 'brew install ffmpeg',
    };
  }

  return {
    ffmpegFound: false,
    brewFound: false,
    installMode: 'install-homebrew',
    message: 'ffmpeg is not installed, and Homebrew is required before the app can install it for you.',
    homebrewCommand: HOMEBREW_INSTALL_COMMAND,
    homebrewUrl: HOMEBREW_URL,
  };
}

function attachLineReader(
  stream: NodeJS.ReadableStream | null,
  onLine: (line: string) => void,
): void {
  if (!stream) return;

  const reader = createInterface({ input: stream });
  reader.on('line', onLine);
}

function startFfmpegInstall(): CommandStartResult {
  if (installProcess) {
    return { started: false, message: 'ffmpeg installation is already in progress.' };
  }

  const brewPath = findBrew();

  if (!brewPath) {
    const message = 'Homebrew is required before ffmpeg can be installed.';
    updateInstallStatus('error', message);
    return { started: false, message };
  }

  emitInstall({ type: 'installing', active: true });
  updateInstallStatus('warning', 'Installing ffmpeg with Homebrew. This may take a few minutes.');
  emitInstall({ type: 'log', line: `$ ${brewPath} install ffmpeg` });

  installProcess = spawn(brewPath, ['install', 'ffmpeg'], {
    env: process.env,
  });

  attachLineReader(installProcess.stdout, (line) => {
    emitInstall({ type: 'log', line });
  });

  attachLineReader(installProcess.stderr, (line) => {
    emitInstall({ type: 'log', line });
  });

  installProcess.on('close', (code) => {
    installProcess = null;
    emitInstall({ type: 'installing', active: false });

    if (code === 0 && findFfmpeg()) {
      updateInstallStatus('success', 'ffmpeg installed successfully.');
      return;
    }

    updateInstallStatus('error', `Homebrew exited with code ${code ?? 'unknown'}.`);
  });

  installProcess.on('error', (error) => {
    installProcess = null;
    emitInstall({ type: 'installing', active: false });
    updateInstallStatus('error', `Failed to run Homebrew: ${error.message}`);
  });

  return { started: true };
}

function startStrip(rawPath: string): CommandStartResult {
  if (stripProcess) {
    return { started: false, message: 'Metadata removal is already in progress.' };
  }

  const validation = validateVideoFile(rawPath);

  if (!validation.ok) {
    updateStripStatus('error', validation.message);
    return { started: false, message: validation.message };
  }

  const ffmpegPath = findFfmpeg();

  if (!ffmpegPath) {
    const message = 'ffmpeg not found. Install it first.';
    updateStripStatus('error', message);
    return { started: false, message };
  }

  const outputPath = getOutputPath(validation.resolvedPath);
  const args = [
    '-y',
    '-i',
    validation.resolvedPath,
    '-map_metadata',
    '-1',
    '-map_chapters',
    '-1',
    '-c',
    'copy',
    outputPath,
  ];

  emitStrip({ type: 'file', fileName: validation.fileName, resolvedPath: validation.resolvedPath });
  emitStrip({ type: 'processing', active: true });
  updateStripStatus('warning', 'Stripping metadata...');
  emitStrip({
    type: 'log',
    line: `$ ${[ffmpegPath, ...args].map((value) => (value.includes(' ') ? `"${value}"` : value)).join(' ')}`,
    kind: 'command',
  });

  stripProcess = spawn(ffmpegPath, args, {
    env: process.env,
  });

  attachLineReader(stripProcess.stdout, (line) => {
    emitStrip({ type: 'log', line, kind: 'output' });
  });

  attachLineReader(stripProcess.stderr, (line) => {
    emitStrip({ type: 'log', line, kind: 'output' });
  });

  stripProcess.on('close', (code) => {
    stripProcess = null;
    emitStrip({ type: 'processing', active: false });

    if (code === 0) {
      updateStripStatus('success', `Done! Saved to ${outputPath}`);
      return;
    }

    if (existsSync(outputPath)) {
      unlinkSync(outputPath);
    }

    updateStripStatus('error', `ffmpeg exited with code ${code ?? 'unknown'}.`);
  });

  stripProcess.on('error', (error) => {
    stripProcess = null;
    emitStrip({ type: 'processing', active: false });
    updateStripStatus('error', `Failed to run ffmpeg: ${error.message}`);
  });

  return { started: true };
}

app.on('window-all-closed', () => {
  app.quit();
});

app.whenReady().then(() => {
  createMainWindow();

  ipcMain.handle('metadata:checkDependencies', async () => checkDependencies());

  ipcMain.handle('metadata:browseFile', async () => {
    if (!mainWindow) return null;

    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: [
        {
          name: 'Video Files',
          extensions: [...supportedExtensionSet].map((extension) => extension.slice(1)),
        },
      ],
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  ipcMain.handle('metadata:validatePath', async (_event, rawPath: string) => {
    return validateVideoFile(rawPath);
  });

  ipcMain.handle('metadata:stripMetadata', async (_event, rawPath: string) => {
    return startStrip(rawPath);
  });

  ipcMain.handle('metadata:installFfmpeg', async () => {
    return startFfmpegInstall();
  });

  ipcMain.handle('metadata:openExternal', async (_event, url: string) => {
    await shell.openExternal(url);
  });

  ipcMain.handle('metadata:copyText', async (_event, text: string) => {
    clipboard.writeText(text);
  });

  ipcMain.handle('metadata:quitApp', async () => {
    app.quit();
  });
});
