import type {
  CommandStartResult,
  DependencyCheckResult,
  InstallEvent,
  StripEvent,
  ValidationResult,
} from './shared/types';

type Unsubscribe = () => void;

declare global {
  interface Window {
    metadataRemover: {
      checkDependencies: () => Promise<DependencyCheckResult>;
      browseFile: () => Promise<string | null>;
      validatePath: (path: string) => Promise<ValidationResult>;
      stripMetadata: (path: string) => Promise<CommandStartResult>;
      installFfmpeg: () => Promise<CommandStartResult>;
      openExternal: (url: string) => Promise<void>;
      copyText: (text: string) => Promise<void>;
      quitApp: () => Promise<void>;
      onStripEvent: (callback: (event: StripEvent) => void) => Unsubscribe;
      onInstallEvent: (callback: (event: InstallEvent) => void) => Unsubscribe;
    };
  }
}

export {};
