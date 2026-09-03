// Runner: node audit/malloy/run.js [file.malloy ...] [--sql]
// With no files, runs every .malloy in this directory in name order. Executes the final
// `run:` statement in each file; --sql also prints the SQL Malloy generated for it.
//
// Module resolution: @malloydata/malloy and @malloydata/db-duckdb are resolved from the first
// node_modules that has them: this directory, then MALLOY_MODULES, then the install from the
// 2026-08-08 Malloy evaluation. `npm install @malloydata/malloy @malloydata/db-duckdb` here
// is the normal path; the fallback exists because @duckdb/node-api does not build on every
// Windows toolchain.
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const HERE = __dirname;
const REPO = path.resolve(HERE, '..', '..');
process.chdir(REPO);                       // duckdb.table('crm_accounts.csv') resolves from the repo root

const CANDIDATES = [
  path.join(HERE, 'node_modules'),
  process.env.MALLOY_MODULES,
  'C:/Users/dksmi/GitHub/t2t-dbt/malloy-poc/node_modules',
].filter(Boolean);

let req = null;
for (const dir of CANDIDATES) {
  if (fs.existsSync(path.join(dir, '@malloydata', 'malloy'))) {
    req = createRequire(path.join(dir, 'noop.js'));
    break;
  }
}
if (!req) {
  console.error('Could not find @malloydata/malloy. Tried:\n  ' + CANDIDATES.join('\n  '));
  console.error('\nnpm install @malloydata/malloy @malloydata/db-duckdb   (in audit/malloy)');
  process.exit(1);
}

const { DuckDBConnection } = req('@malloydata/db-duckdb');
const { SingleConnectionRuntime } = req('@malloydata/malloy');

const showSql = process.argv.includes('--sql');
let files = process.argv.slice(2).filter(a => !a.startsWith('--'));
if (files.length === 0) {
  files = fs.readdirSync(HERE).filter(f => f.endsWith('.malloy') && /^\d/.test(f)).sort().map(f => path.join(HERE, f));
}

(async () => {
  const conn = new DuckDBConnection('duckdb', ':memory:');
  const runtime = new SingleConnectionRuntime({ connection: conn });
  let failed = 0;
  // Every query file is loaded with model.malloy prepended, so `import` is not needed and the
  // model is written once. (The runtime is constructed without a URL reader on purpose.)
  const model = fs.readFileSync(path.join(HERE, 'model.malloy'), 'utf8');
  for (const file of files) {
    const own = fs.readFileSync(file, 'utf8').replace(/^\s*import\s+"model\.malloy"\s*$/m, '');
    const src = model + '\n' + own;
    console.log('\n' + '='.repeat(100) + '\n' + path.basename(file) + '\n' + '='.repeat(100));
    try {
      const result = await runtime.loadQuery(src).run();
      console.table(result.data.toObject());
      if (showSql) console.log('\n--- generated SQL ---\n' + result.sql);
    } catch (e) {
      failed++;
      console.error('\n*** Malloy error ***');
      console.error(e.message);
      for (const p of e.problems || []) {
        const line = p.at?.range?.start?.line;
        if (line !== undefined) console.error(`   line ${line + 1}: ${src.split('\n')[line]?.trim()}`);
      }
    }
  }
  await conn.close();
  process.exit(failed ? 1 : 0);
})();
