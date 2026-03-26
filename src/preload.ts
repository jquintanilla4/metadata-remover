import { contextBridge, ipcRenderer, webUtils } from 'electron';

import type {
  CommandStartResult,
  DependencyCheckResult,
  InstallEvent,
  StripEvent,
  ValidationResult,
} from './shared/types';

const api = {
  checkDependencies: (): Promise<DependencyCheckResult> =>
    ipcRenderer.invoke('metadata:checkDependencies'),
  browseFile: (): Promise<string | null> => ipcRenderer.invoke('metadata:browseFile'),
  getDroppedPath: (file: File): string | null => {
    try {
      return webUtils.getPathForFile(file) || null;
    } catch {
      return null;
    }
  },
  validatePath: (rawPath: string): Promise<ValidationResult> =>
    ipcRenderer.invoke('metadata:validatePath', rawPath),
  stripMetadata: (rawPath: string): Promise<CommandStartResult> =>
    ipcRenderer.invoke('metadata:stripMetadata', rawPath),
  installFfmpeg: (): Promise<CommandStartResult> =>
    ipcRenderer.invoke('metadata:installFfmpeg'),
  openExternal: (url: string): Promise<void> =>
    ipcRenderer.invoke('metadata:openExternal', url),
  copyText: (text: string): Promise<void> =>
    ipcRenderer.invoke('metadata:copyText', text),
  quitApp: (): Promise<void> => ipcRenderer.invoke('metadata:quitApp'),
  onStripEvent: (callback: (event: StripEvent) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, payload: StripEvent) => callback(payload);
    ipcRenderer.on('metadata:stripEvent', listener);
    return () => ipcRenderer.removeListener('metadata:stripEvent', listener);
  },
  onInstallEvent: (callback: (event: InstallEvent) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, payload: InstallEvent) => callback(payload);
    ipcRenderer.on('metadata:installEvent', listener);
    return () => ipcRenderer.removeListener('metadata:installEvent', listener);
  },
};

contextBridge.exposeInMainWorld('metadataRemover', api);
