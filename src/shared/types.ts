export type StatusLevel = 'info' | 'success' | 'warning' | 'error';

export type InstallMode = 'ready' | 'install-ffmpeg' | 'install-homebrew';

export type DependencyCheckResult = {
  ffmpegFound: boolean;
  brewFound: boolean;
  installMode: InstallMode;
  message: string;
  installCommand?: string;
  homebrewCommand?: string;
  homebrewUrl?: string;
};

export type ValidationResult =
  | {
      ok: true;
      resolvedPath: string;
      fileName: string;
    }
  | {
      ok: false;
      message: string;
    };

export type CommandStartResult = {
  started: boolean;
  message?: string;
};

export type StripEvent =
  | {
      type: 'processing';
      active: boolean;
    }
  | {
      type: 'status';
      level: StatusLevel;
      message: string;
    }
  | {
      type: 'file';
      fileName: string;
      resolvedPath: string;
    }
  | {
      type: 'log';
      line: string;
      kind: 'command' | 'output';
    };

export type InstallEvent =
  | {
      type: 'installing';
      active: boolean;
    }
  | {
      type: 'status';
      level: StatusLevel;
      message: string;
    }
  | {
      type: 'log';
      line: string;
    };
