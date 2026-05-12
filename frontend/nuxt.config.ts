export default defineNuxtConfig({
  devtools: { enabled: false },
  css: [],
  modules: ["@pinia/nuxt"],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000",
      wsBase: process.env.NUXT_PUBLIC_WS_BASE || "ws://localhost:8005",
    },
  },
  compatibilityDate: "2024-11-01",
});
