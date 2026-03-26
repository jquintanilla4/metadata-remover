import type { Configuration } from 'webpack';
import type { RuleSetRule } from 'webpack';

import { rules } from './webpack.rules';

const watchOptions: Configuration['watchOptions'] = {
  ignored: ['**/node_modules/**', '**/.git/**', '**/.webpack/**', '**/out/**'],
  poll: 1000,
  aggregateTimeout: 300,
};

const rendererRules = rules.filter((rule) => {
  if (typeof rule !== 'object' || rule === null) {
    return true;
  }

  const normalizedRule = rule as RuleSetRule;
  const useEntries = Array.isArray(normalizedRule.use)
    ? normalizedRule.use
    : normalizedRule.use
      ? [normalizedRule.use]
      : [];

  return !useEntries.some((entry) => {
    if (typeof entry === 'string') {
      return entry.includes('@vercel/webpack-asset-relocator-loader');
    }

    if (typeof entry === 'object' && entry !== null && 'loader' in entry) {
      return String(entry.loader).includes('@vercel/webpack-asset-relocator-loader');
    }

    return false;
  });
});

export const rendererConfig: Configuration = {
  devtool: 'source-map',
  module: {
    rules: [
      ...rendererRules,
      {
        test: /\.css$/,
        use: [{ loader: 'style-loader' }, { loader: 'css-loader' }],
      },
    ],
  },
  node: {
    __dirname: true,
    __filename: true,
  },
  watchOptions,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
  },
};
