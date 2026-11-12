import fs from 'node:fs';
import http from 'node:http';
import { createHash, randomBytes, createSign } from 'node:crypto';
import { readJSON, saveJSON } from './core.mjs';

const SCOPE = 'https://www.googleapis.com/auth/documents';
const TOKEN_URL = 'https://oauth2.googleapis.com/token';
const API = 'https://docs.googleapis.com/v1/documents/';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function request(url, options = {}, attempts = 3) {
  for (let i = 0; ; i++) {
    let r;
    try { r = await fetch(url, { ...options, signal: AbortSignal.timeout(30000) }); }
    catch { if (i + 1 < attempts) { await delay(500 * 2 ** i); continue; } throw new Error('Google network request failed; the pending report remains available for retry.'); }
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { data = {}; }
    if (r.ok) return data;
    if ((r.status === 429 || r.status >= 500) && i + 1 < attempts) { await delay(Math.min(5000, 500 * 2 ** i)); continue; }
    const err = new Error(`Google request failed (HTTP ${r.status}). Check API enablement, document access, credential validity, and revision conflicts.`);
    err.status = r.status;
    err.revisionConflict = r.status === 400 && /revision/i.test(data.error?.message ?? '');
    throw err;
  }
}
async function tokenRequest(fields) {
  const token = await request(TOKEN_URL, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(fields).toString() });
  if (!token.access_token) throw new Error('Google returned no access token.');
  return token;
}
function client(c) {
  const installed = readJSON(c.google.oauthClientFile).installed;
  if (!installed?.client_id || !installed.client_secret) throw new Error('Use a downloaded Google OAuth Desktop app client JSON.');
  return installed;
}
export async function authorize(c) {
  const app = client(c);
  const verifier = randomBytes(48).toString('base64url');
  const state = randomBytes(24).toString('base64url');
  let server, timer;
  try {
    let resolveCode, rejectCode;
    const received = new Promise((resolve, reject) => { resolveCode = resolve; rejectCode = reject; });
    server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://127.0.0.1');
      if (url.pathname !== '/callback') { res.writeHead(404).end(); return; }
      if (url.searchParams.get('state') !== state) { res.writeHead(400).end('Invalid OAuth state.'); return; }
      if (url.searchParams.has('error')) { res.end('Authorization declined. You may close this window.'); rejectCode(new Error('Google authorization declined.')); return; }
      const code = url.searchParams.get('code');
      if (!code) { res.writeHead(400).end('Missing code.'); return; }
      res.end('Authorization received. Return to your terminal.'); resolveCode(code);
    });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    const redirect = `http://127.0.0.1:${server.address().port}/callback`;
    const url = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    url.search = new URLSearchParams({ client_id: app.client_id, redirect_uri: redirect, response_type: 'code', scope: SCOPE,
      access_type: 'offline', prompt: 'consent', state, code_challenge: createHash('sha256').update(verifier).digest('base64url'), code_challenge_method: 'S256' }).toString();
    console.log('Open this Google authorization link in a browser on this computer:\n' + url.href);
    timer = setTimeout(() => rejectCode(new Error('OAuth timed out after five minutes.')), 300000);
    const code = await received;
    const token = await tokenRequest({ client_id: app.client_id, client_secret: app.client_secret, code, code_verifier: verifier, redirect_uri: redirect, grant_type: 'authorization_code' });
    if (!token.refresh_token) throw new Error('No refresh token returned. Revoke the previous grant and authorize again.');
    saveJSON(c.google.tokenFile, { refresh_token: token.refresh_token, scope: token.scope ?? SCOPE });
    console.log('Google refresh credential saved to the configured private token file.');
  } finally { clearTimeout(timer); if (server) await new Promise(resolve => server.close(resolve)); }
}
export async function accessToken(c) {
  if (c.google.authMode === 'oauth') {
    const app = client(c), token = readJSON(c.google.tokenFile);
    return (await tokenRequest({ client_id: app.client_id, client_secret: app.client_secret, refresh_token: token.refresh_token, grant_type: 'refresh_token' })).access_token;
  }
  if (c.google.authMode === 'service_account') {
    const key = readJSON(c.google.serviceAccountFile);
    if (key.type !== 'service_account' || !key.client_email || !key.private_key) throw new Error('Invalid service-account credential file.');
    const issued = Math.floor(Date.now() / 1000);
    const enc = x => Buffer.from(JSON.stringify(x)).toString('base64url');
    const unsigned = enc({ alg: 'RS256', typ: 'JWT' }) + '.' + enc({ iss: key.client_email, scope: SCOPE, aud: TOKEN_URL, iat: issued, exp: issued + 3600 });
    const signature = createSign('RSA-SHA256').update(unsigned).sign(key.private_key, 'base64url');
    return (await tokenRequest({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: unsigned + '.' + signature })).access_token;
  }
  throw new Error('google.authMode must be oauth or service_account.');
}
export function flattenTabs(tabs = []) { return tabs.flatMap(t => [t, ...flattenTabs(t.childTabs)]); }
function googleConfig(c, needTab = true) {
  if (!/^[A-Za-z0-9_-]+$/.test(c.google.documentId ?? '') || c.google.documentId.includes('FILL')) throw new Error('Fill google.documentId with the ID, not its URL.');
  if (needTab && (!c.google.tabId || c.google.tabId.includes('FILL'))) throw new Error('Run google-inspect and fill google.tabId.');
}
export function managedUpdate(doc, tabId, report, agentId) {
  const tab = flattenTabs(doc.tabs).find(t => t.tabProperties?.tabId === tabId);
  if (!tab?.documentTab?.body) throw new Error('Configured Google tab not found.');
  if (!doc.revisionId) throw new Error('Google document has no revisionId; cannot protect concurrent edits.');
  const begin = `[[PROJECT_SCRIBE_BEGIN:${agentId}]]`;
  const end = `[[PROJECT_SCRIBE_END:${agentId}]]`;
  if (report.includes('[[PROJECT_SCRIBE_')) throw new Error('Report contains a reserved publishing marker.');
  const desired = `${begin}\n${report.trimEnd()}\n${end}`;
  const content = tab.documentTab.body.content ?? [];
  // Map characters to Google UTF-16 indexes; only plain top-level paragraphs may contain our block.
  let text = '', positions = [];
  const structures = [];
  for (const item of content) {
    if (item.paragraph) {
      for (const element of item.paragraph.elements ?? []) {
        if (element.textRun) {
          const str = element.textRun.content ?? '';
          for (let i = 0; i < str.length; i++) positions.push(element.startIndex + i);
          text += str;
        } else structures.push({ startIndex: element.startIndex, endIndex: element.endIndex });
      }
    } else if (!item.sectionBreak) structures.push(item);
  }
  const occurrences = needle => text.split(needle).length - 1;
  const b = text.indexOf(begin), z = text.indexOf(end);
  let start, finish;
  if (b < 0 && z < 0) {
    if (text.trim() || structures.length) throw new Error('Target tab is not empty and has no managed block. Add the two exact markers on separate lines or use a blank tab.');
    start = 1; finish = 1;
  } else {
    if (occurrences(begin) !== 1 || occurrences(end) !== 1 || z < b) throw new Error('Managed markers are missing, duplicated, or reversed. Repair them before retrying.');
    start = positions[b]; finish = positions[z + end.length - 1] + 1;
    if (structures.some(x => x.startIndex < finish && x.endIndex > start)) throw new Error('Managed block contains non-text content; use plain paragraphs.');
    for (let i = b + 1; i < z + end.length; i++) {
      if (positions[i] !== positions[i - 1] + 1) throw new Error('Managed block has non-contiguous content; no changes made.');
    }
    if (text.slice(b, z + end.length) === desired) return null;
  }
  const requests = [];
  if (finish > start) requests.push({ deleteContentRange: { range: { startIndex: start, endIndex: finish, tabId } } });
  requests.push({ insertText: { location: { index: start, tabId }, text: desired } });
  return { writeControl: { requiredRevisionId: doc.revisionId }, requests };
}
export async function inspect(c) {
  googleConfig(c, false);
  const token = await accessToken(c);
  const doc = await request(API + encodeURIComponent(c.google.documentId) + '?includeTabsContent=true', { headers: { Authorization: `Bearer ${token}` } });
  return { title: doc.title, tabs: flattenTabs(doc.tabs).map(t => ({ id: t.tabProperties.tabId, title: t.tabProperties.title })) };
}
export async function publish(c, report, transport) {
  if (!c.google.enabled) throw new Error('Google publishing is disabled in config.');
  googleConfig(c);
  const io = transport ?? {
    token: () => accessToken(c),
    get: token => request(API + encodeURIComponent(c.google.documentId) + '?includeTabsContent=true', { headers: { Authorization: `Bearer ${token}` } }),
    // Never blindly replay writes: reread and rebuild on transient or ambiguous errors.
    put: (token, body) => request(API + encodeURIComponent(c.google.documentId) + ':batchUpdate', { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, 1)
  };
  const token = await io.token();
  for (let attempt = 0; attempt < 3; attempt++) {
    const doc = await io.get(token);
    const body = managedUpdate(doc, c.google.tabId, report, c.openclaw.agentId);
    if (!body) return { unchanged: true };
    try { await io.put(token, body); return { published: true }; }
    catch (error) {
      if (attempt === 2 || (error.status && !error.revisionConflict && error.status !== 429 && error.status < 500)) throw error;
      await delay(300 * (attempt + 1));
    }
  }
}
