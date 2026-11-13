import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { capture, normalizeHook, database, evidence, getState, insertEvent, loadConfig, saveJSON, command, snapshot, redact, excluded, extractDigest, validateDigest, sections, withLock, replaySpool } from '../lib/core.mjs';
import { managedUpdate, publish } from '../lib/google.mjs';
import { mergeHooks, hooks, packageDir, cliFile } from '../lib/setup.mjs';
import { reportRun } from '../scribe.mjs';

const scratch = process.env.SCRIBE_TEST_TMP || os.tmpdir();
function fixture(t, commit = true) {
  const dir = fs.mkdtempSync(path.join(scratch, 'scribe-test-'));
  t.after(() => {
    const target = fs.realpathSync(dir), base = fs.realpathSync(scratch);
    const rel = path.relative(base, target);
    if (!rel || rel.startsWith('..') || path.isAbsolute(rel) || !path.basename(target).startsWith('scribe-test-')) throw new Error('Refusing cleanup outside test temporary directory.');
    fs.rmSync(target, { recursive: true, force: true });
  });
  const root = path.join(dir, 'repo with spaces'); fs.mkdirSync(root);
  const g = args => { const r = command(['git', '-C', root, ...args]); assert.equal(r.status, 0, r.stderr); return r.stdout; };
  g(['init']); g(['config', 'user.email', 'test@example.invalid']); g(['config', 'user.name', 'Scribe Test']);
  if (commit) { fs.writeFileSync(path.join(root, 'README.md'), '# Fixture\n'); g(['add', '.']); g(['commit', '-m', 'Initial fixture']); }
  const c = JSON.parse(fs.readFileSync(path.join(packageDir, 'config.example.json'), 'utf8'));
  c.project = { name: 'Fixture', roots: [root] };
  c.stateDir = path.join(dir, 'state'); c.outputDir = path.join(dir, 'reports'); c.workspaceDir = path.join(dir, 'workspace');
  c.openclaw.model = 'example/model'; c.google.documentId = 'fixture-document'; c.google.tabId = 'target';
  c.configFile = path.join(dir, 'config.json'); saveJSON(c.configFile, c);
  return { c: loadConfig(c.configFile), root, dir, g };
}
const hook = (root, extra = {}) => ({ cwd: root, session_id: 'session-a', hook_event_name: 'PostToolUse', tool_name: 'Bash', tool_use_id: randomUUID(), ...extra });
const digest = () => Object.fromEntries(sections.map(k => [k, []]));
function doc(text, extra = {}) {
  return { revisionId: 'revision-one', tabs: [{ tabProperties: { tabId: 'target', title: 'Report' }, documentTab: { body: { content: [
    { startIndex: 0, endIndex: 1, sectionBreak: {} },
    { startIndex: 1, endIndex: text.length + 1, paragraph: { elements: [{ startIndex: 1, endIndex: text.length + 1, textRun: { content: text } }] } }
  ] } } }], ...extra };
}
const begin = '[[PROJECT_SCRIBE_BEGIN:project-scribe]]', end = '[[PROJECT_SCRIBE_END:project-scribe]]';

test('capture is project-scoped, redacts secrets, retains subagent and explicit exit status', t => {
  const { c, root, dir } = fixture(t);
  const e = normalizeHook(c, 'codex', hook(root, { agent_id: 'child', last_assistant_message: 'api_key=secretvalue sk-12345678901234567890', tool_response: { exit_code: 1, stdout: 'private output' } }));
  assert.equal(e.subagent_id, 'child'); assert.equal(e.exit_code, 1); assert.equal(e.tool_result, '');
  assert(!e.message.includes('secretvalue')); assert(!e.message.includes('sk-123'));
  assert.equal(normalizeHook(c, 'codex', hook(dir)), null);
  assert.equal(normalizeHook(c, 'claude', hook(root + '-other')), null);
});
test('deduplicates stable tool IDs without dropping distinct Claude Stop events', t => {
  const { c, root } = fixture(t);
  const raw = hook(root); capture(c, 'codex', raw); capture(c, 'codex', raw);
  const stop = hook(root, { tool_use_id: undefined, hook_event_name: 'Stop', last_assistant_message: 'done' });
  capture(c, 'claude', stop); capture(c, 'claude', stop);
  const db = database(c); assert.equal(db.prepare('SELECT COUNT(*) AS n FROM events').get().n, 3); db.close();
});
test('captures simultaneous CLI processes with valid JSON hook output', async t => {
  const { c, root } = fixture(t);
  const results = await Promise.all(Array.from({ length: 8 }, (_, i) => new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['--no-warnings', cliFile, 'capture', '--config', c.configFile, '--provider', i % 2 ? 'claude' : 'codex'], { windowsHide: true });
    let out = '', err = ''; child.stdout.on('data', x => out += x); child.stderr.on('data', x => err += x);
    child.on('error', reject); child.on('close', code => resolve({ code, out, err }));
    child.stdin.end(JSON.stringify(hook(root, { session_id: 'session-' + i })));
  })));
  for (const result of results) { assert.equal(result.code, 0); assert.deepEqual(JSON.parse(result.out), {}); assert.equal(result.err, ''); }
  const db = database(c); replaySpool(c, db); assert.equal(db.prepare('SELECT COUNT(*) AS n FROM events').get().n, 8); db.close();
});
test('Git captures staged, unstaged, untracked and newly committed changes', t => {
  const { c, root, g } = fixture(t);
  const first = snapshot(c);
  fs.writeFileSync(path.join(root, 'README.md'), '# Updated\n'); g(['add', 'README.md']);
  fs.appendFileSync(path.join(root, 'README.md'), 'unstaged\n');
  fs.writeFileSync(path.join(root, 'new.txt'), 'new');
  let s = snapshot(c, first)[0]; assert(s.staged.includes('README')); assert(s.unstaged.includes('README')); assert(s.status.includes('new.txt'));
  g(['add', '.']); g(['commit', '-m', 'Second change']);
  s = snapshot(c, first)[0]; assert(s.commits.includes('Second change')); assert(s.committed_changes.includes('new.txt')); assert(s.history_continuous);
});
test('supports unborn repositories and detached HEAD', t => {
  const { c, root, g } = fixture(t, false); assert.equal(snapshot(c)[0].head, null);
  fs.writeFileSync(path.join(root, 'x'), 'x'); g(['add', '.']); g(['commit', '-m', 'First']); g(['checkout', '--detach']);
  assert.match(snapshot(c)[0].branch, /detached/);
});
test('separate worktrees are explicit and accurately scoped', t => {
  const { c, root, dir, g } = fixture(t);
  const worktree = path.join(dir, 'other-worktree'); g(['worktree', 'add', '-b', 'parallel', worktree]);
  assert.equal(normalizeHook(c, 'claude', hook(worktree)), null);
  c.project.roots.push(fs.realpathSync(worktree));
  assert.equal(normalizeHook(c, 'claude', hook(worktree)).root, fs.realpathSync(worktree));
  assert.equal(snapshot(c).length, 2);
});
test('excludes secret paths and refuses source traversal', t => {
  const { c, root } = fixture(t);
  for (const p of ['.env', 'a/.env', 'credentials-prod.json', 'a/token-1.json', 'private.key']) assert(excluded(c, p), p);
  fs.writeFileSync(path.join(root, '.env'), 'VERY_PRIVATE=1');
  assert(!snapshot(c)[0].status.includes('.env'));
  c.git.sourceFiles = [{ root: 0, path: '../config.json' }]; assert.throws(() => snapshot(c), /escapes/);
  c.git.sourceFiles = [{ root: 0, path: '.env' }]; assert.throws(() => snapshot(c), /excluded/);
});
test('source excerpts and patches are explicit, bounded and redacted', t => {
  const { c, root } = fixture(t); c.git.sourceFiles = [{ root: 0, path: 'README.md' }]; c.git.includePatches = true;
  fs.writeFileSync(path.join(root, 'README.md'), 'password=not-for-report\n');
  const s = snapshot(c)[0]; assert.equal(s.sources[0].ref, 'source:0:0'); assert(!s.sources[0].text.includes('not-for-report')); assert(!s.patches.includes('not-for-report'));
});
test('evidence pagination retains all records and preview never checkpoints', async t => {
  const { c, root } = fixture(t); c.maxEventsPerReport = 2;
  for (let i = 0; i < 5; i++) capture(c, 'codex', hook(root));
  await reportRun(c, true);
  const db = database(c); const e = evidence(c, db);
  assert.equal(e.events.length, 2); assert.equal(e.pending_after_batch, 3); assert.equal(getState(db, 'checkpoint'), null); db.close();
});
test('model output must use known evidence IDs and exact schema', t => {
  const { c } = fixture(t); const db = database(c), e = evidence(c, db); db.close();
  const d = digest(); d.overview.push({ text: 'Observed project', refs: ['git:0'] });
  assert.deepEqual(extractDigest({ result: { payloads: [{ text: JSON.stringify(d) }] } }, e), d);
  d.overview[0].refs = ['event:999999']; assert.throws(() => validateDigest(d, e), /citation/);
  assert.throws(() => extractDigest({ status: 'error' }, e), /did not complete/);
});
test('unknown OpenClaw JSON shapes fail instead of inventing content', () => {
  assert.throws(() => extractDigest({ response: 'Done' }, {}), /Unknown/);
});
test('publishing initializes blank tab, protects revisions and uses UTF-16 indexes', () => {
  const b = managedUpdate(doc('\n'), 'target', 'Report 😀', 'project-scribe');
  assert.equal(b.writeControl.requiredRevisionId, 'revision-one'); assert.equal(b.requests.length, 1); assert.equal(b.requests[0].insertText.location.tabId, 'target');
  const prefix = 'Human 😀 notes\n', old = `${begin}\nold\n${end}`;
  const update = managedUpdate(doc(prefix + old + '\nHuman suffix\n'), 'target', 'new 😀', 'project-scribe');
  const range = update.requests[0].deleteContentRange.range;
  assert.equal(range.startIndex, prefix.length + 1); assert.equal(range.endIndex, prefix.length + old.length + 1);
});
test('refuses unmarked nonempty tabs, duplicate markers and missing tab IDs', () => {
  assert.throws(() => managedUpdate(doc('Human report\n'), 'target', 'new', 'project-scribe'), /not empty/);
  assert.throws(() => managedUpdate(doc(`${begin}\n${begin}\n${end}\n`), 'target', 'new', 'project-scribe'), /duplicated/);
  assert.throws(() => managedUpdate(doc('\n'), 'wrong', 'new', 'project-scribe'), /not found/);
});
test('handles nested Google tabs and idempotent content', () => {
  const d = doc(`${begin}\nsame 😀\n${end}\n`), target = d.tabs[0];
  d.tabs = [{ tabProperties: { tabId: 'parent' }, childTabs: [target] }];
  assert.equal(managedUpdate(d, 'target', 'same 😀\n', 'project-scribe'), null);
});
test('rejects nontext content in the managed range', () => {
  const d = doc(`${begin}\nold\n${end}\n`);
  d.tabs[0].documentTab.body.content.push({ startIndex: begin.length + 2, endIndex: begin.length + 3, table: {} });
  assert.throws(() => managedUpdate(d, 'target', 'new', 'project-scribe'), /non-text/);
});
test('ambiguous network write retries by reading and finding the already-applied block', async t => {
  const { c } = fixture(t); c.google.enabled = true;
  let current = doc('\n'), writes = 0;
  const result = await publish(c, 'new', { token: async () => 'fake', get: async () => current, put: async (_token, body) => {
    writes++; current = doc(body.requests.at(-1).insertText.text + '\n'); throw new Error('connection lost after commit');
  } });
  assert.equal(writes, 1); assert.equal(result.unchanged, true);
});
test('Google 403 fails without repeated writes', async t => {
  const { c } = fixture(t); c.google.enabled = true; let writes = 0;
  await assert.rejects(publish(c, 'new', { token: async () => 'fake', get: async () => doc('\n'), put: async () => { writes++; throw Object.assign(new Error('forbidden'), { status: 403 }); } }), /forbidden/);
  assert.equal(writes, 1);
});
test('failed publication preserves pending report and cursor; retry reuses synthesis', async t => {
  const { c, root } = fixture(t); c.google.enabled = true; capture(c, 'claude', hook(root));
  let syntheses = 0, publications = 0;
  const services = { synthesize: async () => { syntheses++; return digest(); }, publish: async () => { publications++; if (publications === 1) throw new Error('temporary failure'); return { published: true }; } };
  await assert.rejects(reportRun(c, false, services), /temporary failure/);
  let db = database(c); assert.equal(getState(db, 'checkpoint'), null); db.close();
  assert(fs.existsSync(path.join(c.stateDir, 'pending-report.json')));
  await reportRun(c, false, services);
  db = database(c); assert.equal(getState(db, 'checkpoint').cursor, 1); db.close();
  assert.equal(syntheses, 1); assert.equal(publications, 2); assert(fs.existsSync(path.join(c.outputDir, 'latest.md')));
});
test('unchanged repository and no events skip subsequent model calls', async t => {
  const { c } = fixture(t); let calls = 0;
  const services = { synthesize: async () => { calls++; return digest(); } };
  await reportRun(c, false, services);
  assert.deepEqual(await reportRun(c, false, services), { unchanged: true }); assert.equal(calls, 1);
});
test('merging hooks preserves existing settings and is idempotent', t => {
  const { c } = fixture(t);
  const original = { permissions: { allow: ['Read'] }, hooks: { Stop: [{ hooks: [{ type: 'command', command: 'existing' }] }] } };
  const addition = hooks(c, 'codex'), merged = mergeHooks(original, addition);
  assert.deepEqual(merged.permissions, original.permissions); assert.equal(merged.hooks.Stop.length, 2);
  assert.deepEqual(mergeHooks(merged, addition), merged);
  assert(!('PostToolUseFailure' in addition.hooks));
  assert('PostToolUseFailure' in hooks(c, 'claude').hooks);
});
test('Windows Codex hook wrapper round-trips stdin and paths with spaces', { skip: process.platform !== 'win32' }, t => {
  const { c, root } = fixture(t);
  const handler = hooks(c, 'codex').hooks.Stop[0].hooks[0];
  const encoded = handler.commandWindows.split(' ').at(-1);
  const r = command(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], { input: JSON.stringify(hook(root, { hook_event_name: 'Stop' })) });
  assert.equal(r.status, 0, r.stderr); assert.deepEqual(JSON.parse(r.stdout), {});
  const db = database(c); assert.equal(db.prepare('SELECT COUNT(*) AS n FROM events').get().n, 1); db.close();
});
test('malformed hook input remains non-blocking', t => {
  const { c } = fixture(t);
  const r = command([process.execPath, '--no-warnings', cliFile, 'capture', '--provider', 'codex', '--config', c.configFile], { input: '{bad' });
  assert.equal(r.status, 0); assert.deepEqual(JSON.parse(r.stdout), {}); assert.match(r.stderr, /capture failed/);
});
test('local test wrapper records nonzero exit and returns failure status', t => {
  const { c, root } = fixture(t);
  const r = command([process.execPath, '--no-warnings', cliFile, 'record-test', '--config', c.configFile, '--root', root, '--', process.execPath, '-e', 'console.log("intentional failure"); process.exit(3)']);
  assert.equal(r.status, 1);
  const db = database(c); const e = JSON.parse(db.prepare('SELECT payload FROM events').get().payload); db.close();
  assert.equal(e.exit_code, 3); assert.equal(e.provenance, 'test-wrapper'); assert(e.tool_result.includes('intentional failure'));
});
test('run lock refuses overlap and is released after failure', async t => {
  const { c } = fixture(t);
  await assert.rejects(withLock(c, async () => { await assert.rejects(withLock(c, async () => null), /run.lock/); throw new Error('test failure'); }), /test failure/);
  assert(!fs.existsSync(path.join(c.stateDir, 'run.lock')));
});
test('complete package CLI flow with a simulated OpenClaw validates argv and generated config', t => {
  const { c, dir, root } = fixture(t);
  const mock = path.join(dir, 'mock-openclaw.mjs');
  fs.writeFileSync(mock, `import fs from 'node:fs';
const args = process.argv.slice(2);
const store = ${JSON.stringify(path.join(dir, 'mock-config.json'))};
const entryKey = 'project-scribe';
if (args.includes('--help')) console.log('--workspace --model --non-interactive --agent --session-id --message-file --timeout --json --file --dry-run --every --command-argv --command-cwd --no-deliver --timeout-seconds');
else if (args[0] === '--version') console.log('SIMULATED OpenClaw test adapter');
else if (args[0] === 'agents' && args[1] === 'list') console.log(JSON.stringify(fs.existsSync(store) ? [{id: entryKey, workspace: JSON.parse(fs.readFileSync(store)).workspace}] : []));
else if (args[0] === 'agents' && args[1] === 'add') console.log('{}');
else if (args[0] === 'config' && args[1] === 'patch') {
 const p = JSON.parse(fs.readFileSync(args[args.indexOf('--file')+1]));
 if (!p.agents.entries[entryKey].tools.deny.includes('*')) process.exit(2);
 if (!args.includes('--dry-run')) fs.writeFileSync(store, JSON.stringify(p.agents.entries[entryKey]));
 console.log('{}');
} else if (args[0] === 'config' && args[1] === 'validate') console.log('{}');
else if (args[0] === 'config' && args[1] === 'get') console.log(fs.readFileSync(store, 'utf8'));
else if (args[0] === 'agent') {
 const prompt = fs.readFileSync(args[args.indexOf('--message-file')+1], 'utf8');
 if (!prompt.startsWith('PROJECT_SCRIBE_SYNTHESIS_V1')) process.exit(3);
 console.log(JSON.stringify({status:'ok',result:{payloads:[{text:JSON.stringify({overview:[{text:'Fixture observed',refs:['git:0']}],architecture:[],completed:[],decisions:[],tests:[],blockers:[],next_steps:[]})}]}}));
} else if (args[0] === 'automations') {
 const argv = JSON.parse(args[args.indexOf('--command-argv')+1]);
 if (argv[3] !== 'run' || !args.includes('--no-deliver')) process.exit(4);
 console.log(JSON.stringify({id:'test-job-id',name:'simulated'}));
} else process.exit(5);
`);
  c.openclaw.command = [process.execPath, mock]; saveJSON(c.configFile, c);
  // setup writes generated files into the package; restore or remove them when the test finishes.
  const generated = path.join(packageDir, 'generated');
  const names = ['openclaw.patch.json', 'claude-hooks.json', 'codex-hooks.json'];
  const originals = new Map(names.map(name => [name, fs.existsSync(path.join(generated, name)) ? fs.readFileSync(path.join(generated, name)) : null]));
  t.after(() => { for (const [name, data] of originals) { const p = path.join(generated, name); if (data) fs.writeFileSync(p, data); else if (fs.existsSync(p)) fs.unlinkSync(p); } });
  const run = args => command([process.execPath, '--no-warnings', cliFile, ...args, '--config', c.configFile]);
  let r = run(['setup', '--apply']); assert.equal(r.status, 0, r.stderr);
  assert(fs.existsSync(path.join(c.workspaceDir, 'skills/project-documentation/SKILL.md')));
  r = run(['verify']); assert.equal(r.status, 0, r.stderr);
  capture(c, 'codex', hook(root));
  r = run(['run']); assert.equal(r.status, 0, r.stderr); assert(fs.readFileSync(path.join(c.outputDir, 'latest.md'), 'utf8').includes('Fixture observed'));
  r = run(['schedule', '--apply']); assert.equal(r.status, 0, r.stderr);
  r = run(['schedule', '--apply']); assert.equal(r.status, 1); assert.match(r.stderr, /receipt already exists/);
});
test('configuration rejects string booleans and unknown CLI options', t => {
  const { c } = fixture(t); c.google.enabled = 'false'; saveJSON(c.configFile, c);
  assert.throws(() => loadConfig(c.configFile), /JSON boolean/);
  const r = command([process.execPath, '--no-warnings', cliFile, 'run', '--dry-run', 'yes', '--config', c.configFile]);
  assert.equal(r.status, 1); assert.match(r.stderr, /Unknown option/);
});
test('pending report config changes refuse a new destination', async t => {
  const { c } = fixture(t); c.google.enabled = true;
  await assert.rejects(reportRun(c, false, { synthesize: async () => digest(), publish: async () => { throw new Error('failed'); } }), /failed/);
  c.google.documentId = 'different-document';
  await assert.rejects(reportRun(c, false, { synthesize: async () => digest() }), /Configuration changed/);
});
test('revision conflict is retried with the new revision', async t => {
  const { c } = fixture(t); c.google.enabled = true; let read = 0, written = [];
  const result = await publish(c, 'new', { token: async () => 'fake', get: async () => doc('\n', { revisionId: 'revision-' + (++read) }), put: async (_token, body) => {
    written.push(body.writeControl.requiredRevisionId);
    if (written.length === 1) throw Object.assign(new Error('revision changed'), { status: 400, revisionConflict: true });
  } });
  assert.equal(result.published, true); assert.deepEqual(written, ['revision-1', 'revision-2']);
});
