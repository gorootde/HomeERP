import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

// One server: the FastAPI backend also serves the built SvelteKit SPA
// (frontend_dist) – exactly how HomeERP runs in production. No SSR dev server,
// so the app is exercised the way real users hit it.
const PORT = 8000;

const py =
  process.platform === 'win32'
    ? path.join('.venv', 'Scripts', 'python.exe')
    : path.join('.venv', 'bin', 'python');

// Isolated data dir – wiped and recreated by global-setup.js before each run.
const E2E_DB = './frontend/e2e-data/homeerp-e2e.db';
const E2E_UPLOADS = './frontend/e2e-data/uploads';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  timeout: 30_000,
  expect: { timeout: 7_500 },

  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        permissions: ['camera'],
        launchOptions: {
          args: [
            '--use-fake-device-for-media-stream',
            '--use-fake-ui-for-media-stream',
          ],
        },
      },
    },
  ],

  // The SPA (frontend_dist) must be built before running – `npm run test:e2e`
  // does that for you. Set PW_NO_SERVER=1 to target a backend you started.
  webServer: process.env.PW_NO_SERVER ? undefined : {
    command:
      `node frontend/tests/e2e/reset-db.js && ` +
      `${py} -m alembic upgrade head && ` +
      `${py} -m uvicorn backend.main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: repoRoot,
    url: `http://127.0.0.1:${PORT}/openapi.json`,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      ...process.env,
      DATABASE_URL: `sqlite:///${E2E_DB}`,
      UPLOADS_DIR: E2E_UPLOADS,
    },
  },
});
