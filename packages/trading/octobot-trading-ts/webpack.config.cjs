const path = require('path');

// CCXT is treated as an external. In the browser it must be loaded separately
// (e.g. via ccxt's own ccxt.browser.min.js); bundling it here would force us
// to polyfill many node-only deps it pulls in optionally (protobufjs, etc.).
module.exports = (env = {}) => {
  const minimize = !!env.minimize;
  return {
    mode: minimize ? 'production' : 'development',
    devtool: minimize ? false : 'source-map',
    target: 'web',
    entry: './dist/index.js',
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: minimize ? 'octobot-trading.browser.min.js' : 'octobot-trading.browser.js',
      library: {
        name: 'octobotTrading',
        type: 'umd',
      },
      globalObject: 'this',
    },
    externals: {
      ccxt: {
        commonjs: 'ccxt',
        commonjs2: 'ccxt',
        amd: 'ccxt',
        root: 'ccxt',
      },
    },
    resolve: {
      extensions: ['.js', '.mjs'],
      fallback: {
        fs: false,
        path: false,
        crypto: false,
        http: false,
        https: false,
        url: false,
      },
    },
    optimization: {
      minimize,
    },
    performance: {
      hints: false,
    },
  };
};
