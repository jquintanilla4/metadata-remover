import { useEffect, useRef, useState } from 'react';
import type { DragEvent } from 'react';

import type {
  DependencyCheckResult,
  InstallEvent,
  StatusLevel,
  StripEvent,
  ValidationResult,
} from './shared/types';

type StatusMessage = {
  level: StatusLevel;
  message: string;
};

type LogEntry = {
  id: number;
  line: string;
  kind: 'command' | 'output';
};

function eventHasFiles(event: DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes('Files');
}

function getDroppedPath(event: DragEvent<HTMLElement>): string | null {
  const [file] = Array.from(event.dataTransfer.files);
  if (!file) return null;

  const droppedFile = file as File & { path?: string };
  return droppedFile.path ?? null;
}

function statusClassName(level: StatusLevel | null): string {
  switch (level) {
    case 'success':
      return 'status success';
    case 'warning':
      return 'status warning';
    case 'error':
      return 'status error';
    default:
      return 'status';
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unexpected application error.';
}

export default function App() {
  const [checkingDependencies, setCheckingDependencies] = useState(true);
  const [dependencyState, setDependencyState] = useState<DependencyCheckResult | null>(null);
  const [installStatus, setInstallStatus] = useState<StatusMessage | null>(null);
  const [installLogs, setInstallLogs] = useState<string[]>([]);
  const [installing, setInstalling] = useState(false);

  const [filePath, setFilePath] = useState('');
  const [dropFileName, setDropFileName] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [stripStatus, setStripStatus] = useState<StatusMessage | null>(null);
  const [stripLogs, setStripLogs] = useState<LogEntry[]>([]);

  const dragCounter = useRef(0);
  const logCounter = useRef(0);
  const skipNextDebouncedValidation = useRef(false);

  const dependencyBlocked =
    checkingDependencies || (dependencyState !== null && dependencyState.installMode !== 'ready');

  useEffect(() => {
    const metadataApi = window.metadataRemover;

    if (!metadataApi) {
      setCheckingDependencies(false);
      setInstallStatus({
        level: 'error',
        message: 'Desktop bridge unavailable. Restart the app.',
      });
      return;
    }

    const unsubscribeStrip = metadataApi.onStripEvent((event: StripEvent) => {
      switch (event.type) {
        case 'processing':
          setProcessing(event.active);
          if (event.active) {
            setStripLogs([]);
          }
          return;
        case 'status':
          setStripStatus({ level: event.level, message: event.message });
          return;
        case 'file':
          skipNextDebouncedValidation.current = true;
          setFilePath(event.resolvedPath);
          setDropFileName(event.fileName);
          return;
        case 'log':
          logCounter.current += 1;
          setStripLogs((current) => [
            ...current,
            { id: logCounter.current, line: event.line, kind: event.kind },
          ]);
          return;
      }
    });

    const unsubscribeInstall = metadataApi.onInstallEvent((event: InstallEvent) => {
      switch (event.type) {
        case 'installing':
          setInstalling(event.active);
          if (event.active) {
            setInstallLogs([]);
          }
          return;
        case 'status':
          setInstallStatus({ level: event.level, message: event.message });
          if (event.level === 'success') {
            void refreshDependencies();
          }
          return;
        case 'log':
          setInstallLogs((current) => [...current, event.line]);
          return;
      }
    });

    void refreshDependencies();

    return () => {
      unsubscribeStrip();
      unsubscribeInstall();
    };
  }, []);

  useEffect(() => {
    if (skipNextDebouncedValidation.current) {
      skipNextDebouncedValidation.current = false;
      return;
    }

    if (!filePath.trim()) {
      setDropFileName('');
      setStripStatus(null);
      return;
    }

    if (processing || dependencyBlocked) {
      return;
    }

    const timeout = window.setTimeout(() => {
      void validatePath(filePath);
    }, 300);

    return () => window.clearTimeout(timeout);
  }, [dependencyBlocked, filePath, processing]);

  async function refreshDependencies(): Promise<void> {
    setCheckingDependencies(true);

    try {
      const result = await window.metadataRemover.checkDependencies();
      setDependencyState(result);

      if (result.installMode === 'ready') {
        setInstallStatus(null);
        setInstallLogs([]);
      }
    } catch (error) {
      setDependencyState(null);
      setInstallStatus({
        level: 'error',
        message: `Failed to check dependencies: ${getErrorMessage(error)}`,
      });
    } finally {
      setCheckingDependencies(false);
    }
  }

  async function validatePath(rawPath: string): Promise<ValidationResult> {
    let result: ValidationResult;

    try {
      result = await window.metadataRemover.validatePath(rawPath);
    } catch (error) {
      const message = `Failed to validate path: ${getErrorMessage(error)}`;
      setDropFileName('');
      setStripStatus({ level: 'error', message });
      return { ok: false, message };
    }

    if (result.ok) {
      setDropFileName(result.fileName);
      setStripStatus(null);
    } else if (rawPath.trim()) {
      setDropFileName('');
      setStripStatus({ level: 'error', message: result.message });
    } else {
      setDropFileName('');
      setStripStatus(null);
    }

    return result;
  }

  async function setPathAndMaybeStrip(rawPath: string, autoStrip: boolean): Promise<void> {
    skipNextDebouncedValidation.current = true;
    setFilePath(rawPath);

    const validation = await validatePath(rawPath);

    if (validation.ok && autoStrip) {
      await window.metadataRemover.stripMetadata(validation.resolvedPath);
    }
  }

  async function handleBrowse(): Promise<void> {
    const selectedPath = await window.metadataRemover.browseFile();
    if (!selectedPath) return;

    await setPathAndMaybeStrip(selectedPath, false);
  }

  async function handleStrip(): Promise<void> {
    if (!filePath.trim() || processing) return;
    await window.metadataRemover.stripMetadata(filePath.trim());
  }

  async function handleInstallFfmpeg(): Promise<void> {
    setInstallLogs([]);
    setInstallStatus(null);

    const result = await window.metadataRemover.installFfmpeg();
    if (!result.started && result.message) {
      setInstallStatus({ level: 'error', message: result.message });
    }
  }

  async function handleCopyHomebrewCommand(): Promise<void> {
    if (!dependencyState?.homebrewCommand) return;
    await window.metadataRemover.copyText(dependencyState.homebrewCommand);
    setInstallStatus({ level: 'success', message: 'Homebrew install command copied.' });
  }

  async function handleOpenHomebrew(): Promise<void> {
    if (!dependencyState?.homebrewUrl) return;
    await window.metadataRemover.openExternal(dependencyState.homebrewUrl);
  }

  async function handleQuit(): Promise<void> {
    await window.metadataRemover.quitApp();
  }

  function handleNewSession(): void {
    dragCounter.current = 0;
    setDragActive(false);
    setFilePath('');
    setDropFileName('');
    setStripStatus(null);
    setStripLogs([]);
  }

  function handleDragEnter(event: DragEvent<HTMLDivElement>): void {
    if (!eventHasFiles(event) || processing || dependencyBlocked) return;
    event.preventDefault();
    dragCounter.current += 1;
    setDragActive(true);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>): void {
    if (!eventHasFiles(event) || processing || dependencyBlocked) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    setDragActive(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>): void {
    if (!eventHasFiles(event)) return;
    event.preventDefault();
    dragCounter.current = Math.max(0, dragCounter.current - 1);
    if (dragCounter.current === 0) {
      setDragActive(false);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>): void {
    if (!eventHasFiles(event) || processing || dependencyBlocked) return;
    event.preventDefault();
    dragCounter.current = 0;
    setDragActive(false);

    const droppedPath = getDroppedPath(event);

    if (!droppedPath) {
      setStripStatus({ level: 'error', message: 'Unable to read the dropped file path.' });
      return;
    }

    void setPathAndMaybeStrip(droppedPath, true);
  }

  const dropZoneClassName = [
    'drop-zone',
    dragActive ? 'drag-over' : '',
    dropFileName ? 'has-file' : '',
    processing ? 'processing' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const dependencyMessage =
    installStatus?.message ??
    dependencyState?.message ??
    'Checking for ffmpeg...';

  const showDependencyOverlay = checkingDependencies || dependencyBlocked;
  const showOutputSection = stripLogs.length > 0 || processing;

  return (
    <div className="app-shell">
      <div className="background-grid" />

      {showDependencyOverlay ? (
        <div className="overlay">
          <div className="overlay-card">
            <div className="overlay-title">Dependency Check</div>
            <div className={statusClassName(installStatus?.level ?? null)}>{dependencyMessage}</div>

            {dependencyState?.installMode === 'install-homebrew' ? (
              <>
                <div className="command-card">{dependencyState.homebrewCommand}</div>
                <div className="button-row">
                  <button className="btn-secondary" onClick={() => void handleCopyHomebrewCommand()}>
                    Copy Homebrew Command
                  </button>
                  <button className="btn-primary" onClick={() => void handleOpenHomebrew()}>
                    Open Homebrew
                  </button>
                </div>
                <div className="button-row compact">
                  <button className="btn-ghost" onClick={() => void refreshDependencies()}>
                    Retry Check
                  </button>
                  <button className="btn-ghost" onClick={() => void handleQuit()}>
                    Quit
                  </button>
                </div>
              </>
            ) : null}

            {dependencyState?.installMode === 'install-ffmpeg' ? (
              <>
                {installLogs.length > 0 || installing ? (
                  <div className="install-log">
                    {installLogs.map((line, index) => (
                      <div key={`${line}-${index}`}>{line}</div>
                    ))}
                  </div>
                ) : null}
                <div className="button-row">
                  <button
                    className="btn-primary"
                    disabled={installing}
                    onClick={() => void handleInstallFfmpeg()}
                  >
                    {installing ? 'Installing ffmpeg...' : 'Install ffmpeg'}
                  </button>
                  <button className="btn-ghost" disabled={installing} onClick={() => void handleQuit()}>
                    Quit
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      <main className="app">
        <header className="header">
          <div className="eyebrow">Electron Edition</div>
          <h1>
            Metadata<span>.</span>Remover
          </h1>
          <p>Strip metadata from video files with the user&apos;s installed ffmpeg.</p>
        </header>

        <section className="panel">
          <label className="field-label" htmlFor="file-path">
            File path
          </label>
          <input
            id="file-path"
            className="path-input"
            type="text"
            placeholder="Paste a file path..."
            autoComplete="off"
            spellCheck={false}
            disabled={processing}
            value={filePath}
            onChange={(event) => setFilePath(event.currentTarget.value)}
          />

          <div className="button-row">
            <button
              className="btn-secondary"
              style={{ display: filePath ? 'inline-flex' : 'none' }}
              onClick={handleNewSession}
              disabled={processing}
            >
              New Session
            </button>
            <button className="btn-secondary" onClick={() => void handleBrowse()} disabled={processing}>
              Browse
            </button>
            <button
              className="btn-primary"
              onClick={() => void handleStrip()}
              disabled={processing || !filePath.trim()}
            >
              Strip Metadata
            </button>
          </div>

          <div className={statusClassName(stripStatus?.level ?? null)}>
            {stripStatus?.message ?? ''}
          </div>

          {processing ? (
            <div className="progress-bar">
              <div className="progress-indicator" />
            </div>
          ) : null}
        </section>

        <section
          className={dropZoneClassName}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {!dropFileName ? (
            <div className="drop-label">drag &amp; drop video file here</div>
          ) : (
            <div className="drop-file">{dropFileName}</div>
          )}
        </section>

        {showOutputSection ? (
          <section className="log-panel">
            {stripLogs.map((entry) => (
              <div key={entry.id} className={`log-line ${entry.kind}`}>
                {entry.line}
              </div>
            ))}
          </section>
        ) : null}
      </main>
    </div>
  );
}
