export const SUPPORTED_EXTENSIONS = [
  '.mp4',
  '.mkv',
  '.avi',
  '.mov',
  '.wmv',
  '.flv',
  '.webm',
  '.m4v',
  '.mpg',
  '.mpeg',
  '.3gp',
  '.ts',
] as const;

export const HOMEBREW_INSTALL_COMMAND =
  '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"';

export const HOMEBREW_URL = 'https://brew.sh/';

export const COMMON_FFMPEG_PATHS = [
  '/opt/homebrew/bin/ffmpeg',
  '/usr/local/bin/ffmpeg',
];

export const COMMON_BREW_PATHS = [
  '/opt/homebrew/bin/brew',
  '/usr/local/bin/brew',
];
