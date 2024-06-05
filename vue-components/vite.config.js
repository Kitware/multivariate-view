export default {
  base: "./",
  // resolve: {
  //   alias: {
  //     vue: "vue/dist/vue.esm-bundler.js",
  //   },
  // },
  build: {
    // sourcemap: "inline",
    lib: {
      entry: "./src/main.js",
      name: "multivariate_view",
      formats: ["umd"],
      fileName: "multivariate_view",
    },
    rollupOptions: {
      external: ["vue"],
      output: {
        globals: {
          vue: "Vue",
        },
      },
    },
    outDir: "../multivariate_view/module/serve",
    assetsDir: ".",
  },
};
