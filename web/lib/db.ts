import { Pool } from "pg";

// One pool per process, reused across hot reloads in dev.
const globalForPg = globalThis as unknown as { _pgPool?: Pool };

export const pool =
  globalForPg._pgPool ?? new Pool({ connectionString: process.env.DATABASE_URL });

if (!globalForPg._pgPool) globalForPg._pgPool = pool;
