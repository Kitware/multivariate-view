export default {
  base: "./",
  resolve: {
    alias: {
      vue: "vue/dist/vue.esm-bundler.js",
    },
  },
  build: {
    sourcemap: "inline",
    //   lib: {
    //     entry: "./src/main.js",
    //     name: "trame_radvolviz",
    //     formats: ["umd"],
    //     fileName: "trame_radvolviz",
    //   },
    //   rollupOptions: {
    //     external: ["vue"],
    //     output: {
    //       globals: {
    //         vue: "Vue",
    //       },
    //     },
    //   },
    //   // outDir: "../trame_radvolviz/module/serve",
    //   assetsDir: ".",
  },
};
