const apiVersion = "";
const externals = {};
const path = require("path");
require("webpack");
const pkg = require("./package.json");
const ROOT = path.resolve(__dirname, "src");
const DESTINATION = path.resolve(__dirname, "dist");
const { BundleAnalyzerPlugin } = require("webpack-bundle-analyzer");

module.exports = {
  context: ROOT,
  entry: {
    main: "./index.ts",
  },
  plugins: [
    new BundleAnalyzerPlugin({
      analyzerMode: "static",
      reportFilename: "./bundle-analysis.html",
      openAnalyzer: false,
    }),
  ],
  output: {
    path: DESTINATION,
    libraryTarget: "umd",
    umdNamedDefine: true,
    library: `${pkg.name}_APIv${apiVersion}`,
    filename: pkg.name + ".js",
    globalObject: `(typeof self !== 'undefined' ? self : this)`,
  },
  resolve: {
    extensions: [".ts", "tsx", ".js"],
    modules: [ROOT, "node_modules"],
  },
  externals,
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: [{ loader: "ts-loader" }],
        exclude: /node_modules/,
      },
    ],
  },
  devtool: "source-map",
};
