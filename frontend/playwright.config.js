import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5189',
    trace: 'retain-on-failure',
    ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}),
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: 'npm run dev -- --port 5189',
    url: 'http://127.0.0.1:5189',
    reuseExistingServer: false,
    env: { VITE_API_BASE_URL: 'http://127.0.0.1:8019' },
  },
})
