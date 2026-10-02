import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './integration',
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5190',
    trace: 'retain-on-failure',
    ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}),
  },
  webServer: [
    {
      command: '../backend/.venv/bin/python ../backend/tests/run_browser_api.py',
      url: 'http://127.0.0.1:8029/health',
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
    },
    {
      command: 'npm run dev -- --port 5190',
      url: 'http://127.0.0.1:5190',
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8029' },
    },
  ],
})
