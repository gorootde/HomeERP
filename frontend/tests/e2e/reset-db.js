// Wipe + recreate the isolated E2E data directory. Run from the repo root by
// the Playwright webServer command *before* `alembic upgrade head`, so the
// SQLite file has a directory to live in and every run starts empty.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dataDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../e2e-data');

fs.rmSync(dataDir, { recursive: true, force: true });
fs.mkdirSync(path.join(dataDir, 'uploads'), { recursive: true });

console.log(`[e2e] reset ${dataDir}`);
