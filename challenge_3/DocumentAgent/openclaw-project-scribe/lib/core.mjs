import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createHash, randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';

export const now = () => new Date().toISOString();
export const hash = s => createHash('sha256').update(s).digest('hex');
export function readJSON(p) { return JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '')); }
export function mkdir(p) { fs.mkdirSync(p, { recursive: true, mode: 0o700 }); }
export function atomic(p, data) {
  mkdir(path.dirname(p));
  const tmp = `${p}.${randomUUID()}.tmp`;
  fs.writeFileSync(tmp, data, { mode: 0o600, flag: 'wx' });
  fs.renameSync(tmp, p);
}
export const saveJSON = (p, data) => atomic(p, JSON.stringify(data, null, 2) + '\n');
export function inside(p, root) {
  const rel = path.relative(root, p);
  return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel));
}
function absolute(p, label) {
  if (typeof p !== 'string' || !p || /FILL|<[^>]+>/.test(p)) throw new Error(`Fill ${label} in config.json.`);
  const expanded = p.startsWith('~/') || p.startsWith('~\\') ? path.join(os.homedir(), p.slice(2)) : p;
  if (!path.isAbsolute(expanded)) throw new Error(`${label} must be an absolute path.`);
  return path.normalize(expanded);
}
export function loadConfig(file) {
  const c = readJSON(file);
  if (c.schemaVersion !== 1) throw new Error('Unsupported configuration version.');
  if (!c.project?.name || c.project.name.includes('FILL')) throw new Error('Fill project.name.');
  if (!Array.isArray(c.project.roots) || !c.project.roots.length) throw new Error('Add project.roots.');
  c.project.roots = [...new Set(c.project.roots.map(p => fs.realpathSync(absolute(p, 'project.roots'))))];
  for (const key of ['stateDir', 'outputDir', 'workspaceDir']) {
    let p = absolute(c[key], key), missing = [];
    while (!fs.existsSync(p)) { missing.unshift(path.basename(p)); const parent = path.dirname(p); if (parent === p) throw new Error(`Cannot resolve ${key}.`); p = parent; }
    c[key] = path.join(fs.realpathSync(p), ...missing);
  }
  for (const root of c.project.roots) {
    for (const key of ['stateDir', 'outputDir', 'workspaceDir']) {
      if (inside(c[key], root)) throw new Error(`${key} must be outside observed project roots.`);
    }
    const actual = git(root, ['rev-parse', '--show-toplevel']).trim();
    if (fs.realpathSync(actual) !== root) throw new Error(`Register Git worktree roots, not subdirectories: ${root}`);
  }
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(c.openclaw?.agentId ?? '')) throw new Error('Invalid OpenClaw agentId.');
  if (!Array.isArray(c.openclaw.command) || !c.openclaw.command.length || c.openclaw.command.some(s => typeof s !== 'string' || !s)) throw new Error('openclaw.command must be an argv array.');
  for (const [key, min, max] of [['maxEventsPerReport', 1, 500], ['maxEvidenceChars', 10000, 1000000]]) {
    if (!Number.isInteger(c[key]) || c[key] < min || c[key] > max) throw new Error(`Invalid ${key}.`);
  }
  if (!Number.isInteger(c.openclaw.timeoutSeconds) || c.openclaw.timeoutSeconds < 10 || c.openclaw.timeoutSeconds > 1800) throw new Error('timeoutSeconds must be 10..1800.');
  if (!Number.isInteger(c.capture?.maxTextChars) || c.capture.maxTextChars < 100 || c.capture.maxTextChars > 20000) throw new Error('capture.maxTextChars must be 100..20000.');
  if (!Number.isInteger(c.git?.maxCommits) || c.git.maxCommits < 1 || c.git.maxCommits > 100) throw new Error('git.maxCommits must be 1..100.');
  if (!Number.isInteger(c.git.maxPatchChars) || c.git.maxPatchChars < 100 || c.git.maxPatchChars > 100000) throw new Error('Invalid git.maxPatchChars.');
  for (const [label, value] of [['google.enabled', c.google?.enabled], ['capture.assistantMessages', c.capture.assistantMessages], ['capture.toolResults', c.capture.toolResults], ['git.includePatches', c.git.includePatches]]) {
    if (typeof value !== 'boolean') throw new Error(`${label} must be a JSON boolean.`);
  }
  for (const [label, value] of [['git.excludePaths', c.git.excludePaths], ['capture.redactPatterns', c.capture.redactPatterns]]) {
    if (!Array.isArray(value) || value.some(x => typeof x !== 'string')) throw new Error(`${label} must be an array of strings.`);
  }
  if (!Array.isArray(c.git.sourceFiles) || c.git.sourceFiles.some(x => !x || !Number.isInteger(x.root) || x.root < 0 || x.root >= c.project.roots.length || typeof x.path !== 'string')) throw new Error('Invalid git.sourceFiles.');
  for (const pattern of c.capture.redactPatterns ?? []) new RegExp(pattern, 'g');
  c.configFile = path.resolve(file);
  return c;
}
export function redact(c, value, limit = c.capture.maxTextChars) {
  let s = typeof value === 'string' ? value : JSON.stringify(value ?? '');
  s = s.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '');
  s = s.replace(/-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----/g, '[REDACTED PRIVATE KEY]')
    .replace(/\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|AIza[A-Za-z0-9_-]{25,}|ya29\.[A-Za-z0-9._-]+)/g, '[REDACTED TOKEN]')
    .replace(/\b(Bearer\s+)[A-Za-z0-9._~+/-]+=*/gi, '$1[REDACTED]')
    .replace(/((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client_secret)\s*[=:]\s*["']?)[^\s,"'}]+/gi, '$1[REDACTED]');
  for (const pattern of c.capture.redactPatterns ?? []) s = s.replace(new RegExp(pattern, 'g'), '[REDACTED CUSTOM]');
  return s.length > limit ? s.slice(0, limit) + '\n[TRUNCATED]' : s;
}
export function command(argv, options = {}) {
  const r = spawnSync(argv[0], argv.slice(1), { encoding: 'utf8', windowsHide: true, shell: false,
    timeout: 15000, maxBuffer: 8 * 1024 * 1024, ...options });
  if (r.error) throw new Error(`Cannot execute ${path.basename(argv[0])}: ${r.error.code}. On Windows, configure openclaw.command with node.exe and the absolute OpenClaw .mjs entry, not an npm .cmd shim.`);
  return r;
}
export function git(root, args, optional = false) {
  const r = command(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', root, ...args]);
  if (r.status !== 0 && !optional) throw new Error(`Git ${args[0]} failed for ${root}.`);
  return r.status === 0 ? r.stdout : '';
}
export function database(c) {
  mkdir(c.stateDir);
  const db = new DatabaseSync(path.join(c.stateDir, 'events.db'));
  db.exec(`PRAGMA busy_timeout=2000; PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL,
      recorded_at TEXT NOT NULL, provider TEXT NOT NULL, session_id TEXT NOT NULL, subagent_id TEXT NOT NULL,
      root TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS events_session ON events(provider,session_id,subagent_id,id);
    CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);`);
  return db;
}
export function getState(db, key, fallback = null) {
  const row = db.prepare('SELECT value FROM state WHERE key=?').get(key);
  return row ? JSON.parse(row.value) : fallback;
}
export function setState(db, key, value) {
  db.prepare('INSERT INTO state(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').run(key, JSON.stringify(value));
}
export function insertEvent(db, e) {
  db.prepare('INSERT OR IGNORE INTO events(event_key,recorded_at,provider,session_id,subagent_id,root,payload) VALUES (?,?,?,?,?,?,?)')
    .run(e.event_key, e.recorded_at, e.provider, e.session_id, e.subagent_id, e.root, JSON.stringify(e));
}
export function normalizeHook(c, provider, raw) {
  if (!['claude', 'codex'].includes(provider)) throw new Error('Provider must be claude or codex.');
  if (!raw.cwd || !raw.session_id || !raw.hook_event_name) throw new Error('Hook missing cwd, session_id, or hook_event_name.');
  let cwd;
  try { cwd = fs.realpathSync(raw.cwd); } catch { return null; }
  if (!c.project.roots.some(root => inside(cwd, root))) return null;
  const actual = git(cwd, ['rev-parse', '--show-toplevel'], true).trim();
  if (!actual) return null;
  const root = fs.realpathSync(actual);
  if (!c.project.roots.includes(root)) return null;
  const identity = raw.event_id || (raw.tool_use_id ? `${raw.hook_event_name}:${raw.tool_use_id}` : raw.turn_id ? `${raw.hook_event_name}:${raw.turn_id}:${raw.agent_id ?? ''}` : randomUUID());
  const msg = c.capture.assistantMessages ? raw.last_assistant_message ?? '' : '';
  const response = raw.tool_response;
  const exitCode = typeof response === 'object' && response !== null ? response.exit_code ?? response.exitCode ?? null : null;
  const e = {
    event_key: hash(JSON.stringify([provider, raw.session_id, raw.agent_id ?? '', identity])),
    recorded_at: now(), provider, session_id: String(raw.session_id).slice(0, 300),
    subagent_id: String(raw.agent_id ?? '').slice(0, 300), model: String(raw.model ?? 'unknown').slice(0, 200),
    turn_id: String(raw.turn_id ?? '').slice(0, 300), event_type: String(raw.hook_event_name).slice(0, 100), root, cwd,
    head: git(root, ['rev-parse', '--verify', 'HEAD'], true).trim() || null,
    tool_name: String(raw.tool_name ?? '').slice(0, 200),
    file_path: typeof raw.tool_input?.file_path === 'string' ? redact(c, raw.tool_input.file_path, 1000) : '',
    message: redact(c, msg), exit_code: Number.isInteger(exitCode) ? exitCode : null,
    tool_result: c.capture.toolResults && response != null ? redact(c, response) : '',
    error: raw.error ? redact(c, raw.error) : '', provenance: 'agent-hook'
  };
  // Raw prompts, transcript content, transcript paths, and arbitrary tool inputs are intentionally not retained.
  return e;
}
export function capture(c, provider, raw) {
  const e = normalizeHook(c, provider, raw);
  if (!e) return { ignored: true };
  let db;
  try { db = database(c); insertEvent(db, e); return { captured: true }; }
  catch {
    const spool = path.join(c.stateDir, 'spool'); mkdir(spool);
    saveJSON(path.join(spool, `${randomUUID()}.json`), e);
    return { spooled: true };
  } finally { db?.close(); }
}
export function replaySpool(c, db) {
  const dir = path.join(c.stateDir, 'spool');
  if (!fs.existsSync(dir)) return;
  for (const name of fs.readdirSync(dir).filter(n => n.endsWith('.json'))) {
    const p = path.join(dir, name);
    insertEvent(db, readJSON(p)); fs.unlinkSync(p);
  }
}
function matchesGlob(p, pattern) {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*\*/g, '\u0000').replace(/\*/g, '[^/]*').replace(/\u0000/g, '.*').replace(/\?/g, '.');
  return new RegExp(`^${escaped}$`).test(p.replaceAll('\\', '/'));
}
export const excluded = (c, p) => c.git.excludePaths.some(glob => matchesGlob(p, glob));
export function fingerprint(root) {
  return hash(git(root, ['rev-parse', '--verify', 'HEAD'], true) + git(root, ['diff', '--no-ext-diff', '--no-textconv', '--binary', 'HEAD'], true) + git(root, ['status', '--porcelain=v1', '-uall']));
}
export function snapshot(c, previous = []) {
  return c.project.roots.map((root, i) => {
    const head = git(root, ['rev-parse', '--verify', 'HEAD'], true).trim() || null;
    const pathspec = ['.', ...c.git.excludePaths.map(p => `:(exclude,glob)${p}`)];
    const before = previous.find(p => p.root === root)?.head;
    const ancestor = head && before && command(['git', '-C', root, 'merge-base', '--is-ancestor', before, head]).status === 0;
    const range = ancestor ? `${before}..${head}` : head;
    const s = {
      ref: `git:${i}`, root, head, branch: git(root, ['symbolic-ref', '--short', 'HEAD'], true).trim() || '(detached or unborn)',
      tracked_fingerprint: fingerprint(root),
      base_head: before ?? null, history_continuous: Boolean(ancestor),
      status: git(root, ['status', '--porcelain=v1', '-uall', '--', ...pathspec]),
      staged: git(root, ['diff', '--cached', '--no-ext-diff', '--no-textconv', '--stat', '--', ...pathspec]),
      unstaged: git(root, ['diff', '--no-ext-diff', '--no-textconv', '--stat', '--', ...pathspec]),
      commits: head ? git(root, ['log', `-n${c.git.maxCommits}`, '--format=%h %aI %s', range, '--', ...pathspec]) : '',
      committed_changes: head && ancestor && before !== head ? git(root, ['diff', '--no-ext-diff', '--no-textconv', '--stat', `${before}..${head}`, '--', ...pathspec]) : '',
      patches: '', sources: [], limitations: ['Git status and log are bounded observations, not authorship or test verification. Untracked file contents are not read.']
    };
    if (c.git.includePatches) {
      const baseArgs = ['--no-ext-diff', '--no-textconv', '--unified=3'];
      s.patches = redact(c, git(root, ['diff', ...baseArgs, '--', ...pathspec]) + git(root, ['diff', '--cached', ...baseArgs, '--', ...pathspec]) +
        (head && ancestor && before !== head ? git(root, ['diff', ...baseArgs, `${before}..${head}`, '--', ...pathspec]) : ''), c.git.maxPatchChars);
    } else s.limitations.push('Patch contents disabled.');
    for (const entry of c.git.sourceFiles ?? []) {
      if (entry.root !== i) continue;
      if (typeof entry.path !== 'string' || path.isAbsolute(entry.path) || excluded(c, entry.path)) throw new Error('Invalid or excluded sourceFiles path.');
      const p = fs.realpathSync(path.join(root, entry.path));
      if (!inside(p, root)) throw new Error('Source symlink escapes project root.');
      const stat = fs.statSync(p);
      if (!stat.isFile() || stat.size > 1024 * 1024) throw new Error('Source excerpt must be a regular file under 1 MiB.');
      const content = fs.readFileSync(p, 'utf8');
      if (content.includes('\u0000')) throw new Error('Binary source excerpt refused.');
      s.sources.push({ ref: `source:${i}:${s.sources.length}`, path: entry.path, sha256: hash(content), text: redact(c, content, 12000) });
    }
    for (const key of ['status', 'staged', 'unstaged', 'commits', 'committed_changes']) s[key] = redact(c, s[key], 16000);
    return s;
  });
}
export function evidence(c, db) {
  replaySpool(c, db);
  const checkpoint = getState(db, 'checkpoint', { cursor: 0, snapshots: [] });
  const rows = db.prepare('SELECT id,payload FROM events WHERE id>? ORDER BY id LIMIT ?').all(checkpoint.cursor, c.maxEventsPerReport);
  const events = rows.map(r => ({ ref: `event:${r.id}`, id: r.id, ...JSON.parse(r.payload) }));
  const sessions = db.prepare('SELECT provider,session_id,subagent_id,COUNT(*) AS events,MIN(recorded_at) AS first_seen,MAX(recorded_at) AS last_seen FROM events GROUP BY provider,session_id,subagent_id ORDER BY MAX(id) DESC LIMIT 200').all();
  const total = db.prepare('SELECT COUNT(*) AS n FROM events').get().n;
  const e = { version: 1, project: c.project.name, captured_at: now(),
    cursor_before: checkpoint.cursor, cursor_after: rows.at(-1)?.id ?? checkpoint.cursor,
    events_total: total, pending_after_batch: db.prepare('SELECT COUNT(*) AS n FROM events WHERE id>?').get(rows.at(-1)?.id ?? checkpoint.cursor).n,
    events, sessions, snapshots: snapshot(c, checkpoint.snapshots),
    scope: 'Current batch plus current Git snapshots; older reports and all events are retained locally. Session table is the 200 most recently observed sessions.' };
  if (JSON.stringify(e).length > c.maxEvidenceChars) throw new Error('Evidence exceeds maxEvidenceChars. Reduce maxEventsPerReport, text limits, or source excerpts; no cursor was advanced.');
  return e;
}
export const sections = ['overview', 'architecture', 'completed', 'decisions', 'tests', 'blockers', 'next_steps'];
export function validateDigest(d, e) {
  if (!d || typeof d !== 'object' || Array.isArray(d) || Object.keys(d).some(k => !sections.includes(k))) throw new Error('Invalid synthesis object.');
  const refs = new Set([...e.events.map(v => v.ref), ...e.snapshots.flatMap(s => [s.ref, ...s.sources.map(v => v.ref)])]);
  for (const key of sections) {
    if (!Array.isArray(d[key]) || d[key].length > 12) throw new Error(`Invalid synthesis section ${key}.`);
    for (const item of d[key]) {
      if (!item || Object.keys(item).some(k => !['text', 'refs'].includes(k)) || typeof item.text !== 'string' || !item.text.trim() || item.text.length > 1800 || !Array.isArray(item.refs) || !item.refs.length || item.refs.some(r => !refs.has(r))) throw new Error(`Invalid item or evidence citation in ${key}.`);
    }
  }
  return d;
}
export function extractDigest(envelope, e) {
  if (envelope.ok === false || ['error', 'timeout', 'cancelled'].includes(envelope.status)) throw new Error('OpenClaw did not complete the synthesis.');
  const payloads = envelope.result?.payloads ?? envelope.payloads;
  const text = envelope.final ?? envelope.result?.final ?? payloads?.map(p => p.text ?? '').join('\n');
  if (typeof text !== 'string') throw new Error('Unknown OpenClaw JSON envelope; inspect installed CLI version.');
  return validateDigest(JSON.parse(text.trim().replace(/^```json\s*|\s*```$/g, '')), e);
}
export function render(c, e, digest, reportId) {
  const lines = [`# ${c.project.name} — project documentation`, '', `Report: ${reportId}`, `Observed: ${e.captured_at}`,
    `Coverage: ${e.events.length ? `events ${e.cursor_before + 1}–${e.cursor_after}` : 'no new events'}; ${e.pending_after_batch} queued for a later report; ${e.events_total} events retained.`,
    '', 'This report separates model interpretation, agent claims, Git observations, and recorded command results. Citations identify evidence, not a guarantee that a claim is true.', ''];
  if (digest) {
    lines.push('## OpenClaw synthesis (model interpretation)', '');
    for (const key of sections) {
      lines.push(`### ${key.replaceAll('_', ' ')}`, '');
      lines.push(...(digest[key].length ? digest[key].map(x => `- ${redact(c, x.text, 1800)} [${x.refs.join(', ')}]`) : ['No supported findings in this batch.']), '');
    }
  } else lines.push('## Evidence preview', '', 'No model synthesis or Google Docs write was performed.', '');
  lines.push('## Sessions observed (historical totals)', '');
  for (const s of e.sessions) lines.push(`- ${s.provider} / ${s.session_id}${s.subagent_id ? ' / subagent ' + s.subagent_id : ''}: ${s.events} events; last seen ${s.last_seen}.`);
  if (!e.sessions.length) lines.push('No coding-agent events have been received yet.');
  lines.push('', '## Git evidence', '');
  for (const s of e.snapshots) {
    lines.push(`### [${s.ref}] ${s.root}`, '', `Branch: ${s.branch}; HEAD: ${s.head ?? '(no commits)'}.`,
      `Previous HEAD: ${s.base_head ?? '(first observation)'}; continuous ancestry: ${s.history_continuous}.`, '',
      'Status:', '```text', s.status || '(clean)', '```', 'Staged changes:', '```text', s.staged || '(none)', '```',
      'Unstaged changes:', '```text', s.unstaged || '(none)', '```', 'Committed changes since checkpoint:', '```text', s.committed_changes || '(none or no continuous baseline)', '```',
      'Commits (bounded):', '```text', s.commits || '(none)', '```', ...s.limitations.map(x => `- ${x}`), '');
    for (const source of s.sources) lines.push(`[${source.ref}] Source: ${source.path}; SHA-256 ${source.sha256}`, '```text', source.text, '```', '');
    if (s.patches) lines.push('Patch excerpts:', '```diff', s.patches, '```', '');
  }
  lines.push('## Activity evidence', '');
  for (const ev of e.events) {
    lines.push(`### [${ev.ref}] ${ev.provider} / ${ev.session_id}${ev.subagent_id ? ' / ' + ev.subagent_id : ''}`, '',
      `${ev.recorded_at} — ${ev.event_type}; model: ${ev.model ?? 'unknown'}; HEAD: ${ev.head ?? 'unknown'}.`,
      `Root: ${ev.root}`, `Tool: ${ev.tool_name || '(none)'}; recorded exit: ${ev.exit_code ?? 'not supplied'}.`);
    if (ev.provenance === 'test-wrapper') lines.push(`Recorded command: ${JSON.stringify(ev.command)}; tracked state stable: ${ev.tracked_state_stable}; output SHA-256: ${ev.output_sha256}.`);
    if (ev.message) lines.push('Agent-reported statement:', '```text', ev.message, '```');
    if (ev.error) lines.push('Reported error:', '```text', ev.error, '```');
    if (ev.tool_result) lines.push('Recorded output excerpt:', '```text', ev.tool_result, '```');
    lines.push('');
  }
  lines.push('## Evidence limits', '', 'Hooks observe configured local sessions only. Missing model identifiers remain unknown. A successful tool call or Stop event does not prove a successful test. Shared-worktree changes are not attributable to one session. Source reads and Git snapshots are not atomic with concurrent edits. Test wrapper fingerprints cover HEAD, tracked diffs, and status names, not all untracked bytes. Older reports and events remain local.', '');
  return redact(c, lines.join('\n'), 1000000);
}
export async function withLock(c, fn) {
  mkdir(c.stateDir);
  const p = path.join(c.stateDir, 'run.lock');
  try { fs.writeFileSync(p, JSON.stringify({ pid: process.pid, at: now(), host: os.hostname() }), { flag: 'wx', mode: 0o600 }); }
  catch (err) { if (err.code === 'EEXIST') throw new Error('Another report run holds run.lock. If a prior run crashed, verify its PID has stopped before removing that one lock file.'); throw err; }
  try { return await fn(); } finally { fs.unlinkSync(p); }
}
