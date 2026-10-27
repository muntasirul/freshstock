import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:5173",
  },
  webServer: [
    {
      command: "../../.venv/bin/uvicorn freshstock.api:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: !process.env.CI,
      env: {
        FRESHSTOCK_DATA_DIR: "../../data/processed",
        FRESHSTOCK_ARTIFACT_DIR: "../../artifacts/model",
        FRESHSTOCK_DATABASE_URL: "sqlite:///../../data/freshstock.db",
      },
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
