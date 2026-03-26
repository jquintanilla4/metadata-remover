import type { Configuration } from 'webpack';

import { rules } from './webpack.rules';

const watchOptions: Configuration['watchOptions'] = {
  ignored: ['**/node_modules/**', '**/.git/**', '**/.webpack/**', '**/out/**'],
  poll: 1000,
  aggregateTimeout: 300,
};

export const mainConfig: Configuration = {
  entry: './src/main.ts',
  module: {
    rules,
  },
  watchOptions,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
  },
};
