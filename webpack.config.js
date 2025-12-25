const path = require('path');

module.exports = {
  entry: './static/js/collaboration.tsx',
  output: {
    path: path.resolve(__dirname, 'static/dist'),
    filename: 'collaboration-bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.(ts|tsx)$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },
};
