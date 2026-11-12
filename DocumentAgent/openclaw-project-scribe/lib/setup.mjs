import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { command, mkdir, atomic, readJSON, saveJSON } from './core.mjs';

export const packageDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const cliFile = path.join(packageDir, 'scribe.mjs');
export function claw(c, args, options = {}) {
  const r = command([...c.openclaw.command, ...args], options);
  if (r.status !== 0) throw new Error(`OpenClaw ${args.slice(0, 2).join(' ')} failed (exit ${r.status}). Run that command directly to inspect diagnostics. No credentials or model output are echoed here.`);
  return r.stdout.trim();
}
export const quotePosix = s => "'" + s.replaceAll("'", "'\"'\"'") + "'";
export const quotePS = s => "'" + s.replaceAll("'", "''") + "'";
export function hooks(c, provider) {
  const args = ['--no-warnings', cliFile, 'capture', '--provider', provider, '--config', c.configFile];
  const events = provider === 'claude' ? ['SessionStart', 'PostToolUse', 'PostToolUseFailure', 'SubagentStart', 'SubagentStop', 'Stop'] : ['SessionStart', 'PostToolUse', 'SubagentStart', 'SubagentStop', 'Stop'];
  const handler = provider === 'claude' ? { type: 'command', command: process.execPath, args, timeout: 15 } : {
    type: 'command', command: [process.execPath, ...args].map(quotePosix).join(' '), timeout: 15
  };
  if (provider === 'codex' && process.platform === 'win32') {
    const script = '& ' + [process.execPath, ...args].map(quotePS).join(' ');
    handler.commandWindows = 'powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand ' + Buffer.from(script, 'utf16le').toString('base64');
  }
  return { hooks: Object.fromEntries(events.map(event => [event, [{ hooks: [{ ...handler }] }]])) };
}
export function mergeHooks(original, addition) {
  const merged = structuredClone(original);
  merged.hooks ??= {};
  if (!merged.hooks || typeof merged.hooks !== 'object' || Array.isArray(merged.hooks)) throw new Error('Existing hooks must be an object.');
  for (const [event, groups] of Object.entries(addition.hooks)) {
    merged.hooks[event] ??= [];
    if (!Array.isArray(merged.hooks[event])) throw new Error('Existing event hooks must be arrays.');
    const existing = new Set(merged.hooks[event].map(g => JSON.stringify(g)));
    for (const g of groups) if (!existing.has(JSON.stringify(g))) merged.hooks[event].push(g);
  }
  return merged;
}
export function installHooks(c, provider, target) {
  if (!['claude', 'codex'].includes(provider) || !target || !path.isAbsolute(target)) throw new Error('Supply --provider claude|codex and --target ABSOLUTE_SETTINGS_PATH.');
  const existing = fs.existsSync(target) ? readJSON(target) : {};
  const next = mergeHooks(existing, hooks(c, provider));
  if (JSON.stringify(existing) === JSON.stringify(next)) return { unchanged: true };
  const backup = target + `.scribe-backup-${Date.now()}.json`;
  if (fs.existsSync(target)) fs.copyFileSync(target, backup, fs.constants.COPYFILE_EXCL);
  saveJSON(target, next);
  return { installed: target, backup: fs.existsSync(backup) ? backup : null, next: 'Restart sessions; in Codex, review and trust these hooks with /hooks.' };
}
export function patch(c) {
  if (!c.openclaw.model || c.openclaw.model.includes('FILL')) throw new Error('Fill openclaw.model using a provider/model ID available to your OpenClaw account.');
  return { agents: { entries: { [c.openclaw.agentId]: {
    workspace: c.workspaceDir, model: c.openclaw.model, contextInjection: 'never',
    models: { [c.openclaw.model]: { agentRuntime: { id: 'openclaw' } } },
    skills: ['project-documentation'], tools: { deny: ['*'] }, subagents: { allowAgents: [] }
  } } } };
}
export function checkCLI(c, schedule = false) {
  const checks = [
    [['agents', 'add', '--help'], ['--workspace', '--model', '--non-interactive']],
    [['agent', '--help'], ['--agent', '--session-id', '--message-file', '--timeout', '--json']],
    [['config', 'patch', '--help'], ['--file', '--dry-run']],
    [['config', 'get', '--help'], ['--json']],
    [['config', 'validate', '--help'], []]
  ];
  if (schedule) checks.push([['automations', 'create', '--help'], ['--every', '--command-argv', '--command-cwd', '--no-deliver', '--timeout-seconds']]);
  const version = claw(c, ['--version']);
  for (const [args, flags] of checks) {
    const help = claw(c, args);
    for (const flag of flags) if (!help.includes(flag)) throw new Error(`Installed OpenClaw lacks ${args.slice(0, -1).join(' ')} ${flag}. Update OpenClaw or review SOURCES.md.`);
  }
  return version;
}
export function installWorkspace(c) {
  const files = ['AGENTS.md', 'SOUL.md', 'IDENTITY.md', 'skills/project-documentation/SKILL.md'];
  // Preflight all conflicts before changing any workspace file.
  for (const rel of files) {
    const target = path.join(c.workspaceDir, rel), source = path.join(packageDir, 'workspace', rel);
    if (fs.existsSync(target) && fs.readFileSync(target, 'utf8') !== fs.readFileSync(source, 'utf8')) throw new Error(`Existing workspace file differs: ${target}. Choose a new workspace or merge it manually.`);
  }
  for (const rel of files) {
    const target = path.join(c.workspaceDir, rel);
    if (!fs.existsSync(target)) atomic(target, fs.readFileSync(path.join(packageDir, 'workspace', rel)));
  }
}
export function setup(c, apply = false) {
  const dir = path.join(packageDir, 'generated'); mkdir(dir);
  const patchFile = path.join(dir, 'openclaw.patch.json');
  saveJSON(patchFile, patch(c));
  saveJSON(path.join(dir, 'claude-hooks.json'), hooks(c, 'claude'));
  saveJSON(path.join(dir, 'codex-hooks.json'), hooks(c, 'codex'));
  installWorkspace(c);
  if (!apply) return { prepared: dir, workspace: c.workspaceDir, next: 'Run setup --apply to validate installed CLI capabilities, register the agent, and apply its configuration.' };
  const version = checkCLI(c);
  const roster = JSON.parse(claw(c, ['agents', 'list', '--json']));
  const agents = Array.isArray(roster) ? roster : roster.agents;
  if (!Array.isArray(agents)) throw new Error('Unknown agents list JSON shape. Inspect OpenClaw version before installing.');
  const found = agents.find(a => (a.id ?? a.agentId) === c.openclaw.agentId);
  if (found && (!found.workspace || path.resolve(found.workspace) !== path.resolve(c.workspaceDir))) throw new Error('Agent ID already belongs to another workspace; choose a new ID.');
  if (!found) claw(c, ['agents', 'add', c.openclaw.agentId, '--workspace', c.workspaceDir, '--model', c.openclaw.model, '--non-interactive']);
  claw(c, ['config', 'patch', '--file', patchFile, '--dry-run']);
  claw(c, ['config', 'patch', '--file', patchFile]);
  claw(c, ['config', 'validate']);
  saveJSON(path.join(c.stateDir, 'openclaw-verification.json'), { version, checkedAt: new Date().toISOString(), agentId: c.openclaw.agentId });
  return { installed: true, version, agentId: c.openclaw.agentId };
}
export function assertAgentPolicy(c) {
  const entry = JSON.parse(claw(c, ['config', 'get', `agents.entries.${c.openclaw.agentId}`, '--json']));
  if (!entry.tools?.deny?.includes('*') || entry.contextInjection !== 'never' || entry.models?.[c.openclaw.model]?.agentRuntime?.id !== 'openclaw' ||
      (typeof entry.model === 'string' ? entry.model : entry.model?.primary) !== c.openclaw.model || path.resolve(entry.workspace ?? '') !== path.resolve(c.workspaceDir)) {
    throw new Error('Project Scribe agent configuration differs from the prepared policy. Rerun setup --apply before synthesis.');
  }
}
export function schedule(c, apply = false) {
  if (!/^\d+[smhd]$/.test(c.schedule.every)) throw new Error('schedule.every must be an interval such as 15m or 1h.');
  const args = ['automations', 'create', '--every', c.schedule.every, '--name', `${c.openclaw.agentId}-documentation`,
    '--command-argv', JSON.stringify([process.execPath, '--no-warnings', cliFile, 'run', '--config', c.configFile]),
    '--command-cwd', packageDir, '--timeout-seconds', String(c.openclaw.timeoutSeconds + 180), '--no-deliver'];
  if (!apply) return { command: [...c.openclaw.command, ...args], next: 'Run schedule --apply after a successful manual run. Save the returned job ID.' };
  checkCLI(c, true);
  const receipt = path.join(c.stateDir, 'schedule-receipt.txt');
  if (fs.existsSync(receipt)) throw new Error('A schedule receipt already exists. Inspect it and openclaw automations list before creating another job.');
  const result = claw(c, args);
  atomic(receipt, result + '\n');
  return { created: true, receipt, result };
}
