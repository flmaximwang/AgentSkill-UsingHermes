#!/usr/bin/env node
/**
 * local-cdp-proxy.mjs — minimal CDP proxy for the document-download toolchain family.
 *
 * Implements the contract the downloader skills expect on 127.0.0.1:3456:
 *   GET  /targets                      -> [{targetId,url,title,type,...}]
 *   GET  /info?target=<id>             -> {targetId,url,title,ready}
 *   POST /new        (body=url)        -> {targetId,url,title}
 *   POST /navigate   (body=url,?target=<id>)
 *   POST /eval       (body=js, ?target=<id>) -> {value}
 *   POST /click      (body=selector, ?target=<id>)
 *   GET  /close?target=<id>
 *   GET  /scroll?target=<id>&direction=bottom|top|<px>
 *
 * Node 22+ only (global WebSocket / fetch). No dependencies.
 * Reads no cookies, passwords, localStorage or session files — it drives the browser
 * through the DevTools protocol endpoint the user already opened.
 *
 * Usage: node local-cdp-proxy.mjs [--port 3456] [--cdp http://127.0.0.1:9222]
 */

import http from "node:http";

const args = process.argv.slice(2);
function argOf(name, dflt) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
}
const PORT = Number(argOf("--port", "3456"));
const CDP = argOf("--cdp", "http://127.0.0.1:9222").replace(/\/$/, "");

async function httpJson(url, options = {}) {
  const r = await fetch(url, { ...options, signal: AbortSignal.timeout(20000) });
  const text = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status} ${url}: ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : {};
}

/** Open a CDP session against one page target and expose send(). */
async function withSession(wsUrl, fn) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(`${msg.error.message} (${msg.error.code})`)) : resolve(msg.result);
    }
  });
  await new Promise((res, rej) => {
    ws.addEventListener("open", res, { once: true });
    ws.addEventListener("error", () => rej(new Error("CDP websocket error")), { once: true });
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
      setTimeout(() => {
        if (pending.has(mid)) { pending.delete(mid); reject(new Error(`CDP timeout: ${method}`)); }
      }, 30000);
    });
  try { return await fn(send); } finally { try { ws.close(); } catch {} }
}

const targets = () => httpJson(`${CDP}/json/list`);
async function findTarget(tid) {
  const list = (await targets()).filter((t) => t.type === "page");
  const t = tid ? list.find((x) => x.id === tid) : list[0];
  if (!t) throw new Error(`target not found: ${tid || "(no page target)"}`);
  return t;
}
const shape = (t, ready = null) => ({
  targetId: t.id, url: t.url, title: t.title, type: t.type, ready,
});

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString("utf8");
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const tid = u.searchParams.get("target") || undefined;
  const reply = (code, obj) => {
    res.writeHead(code, { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" });
    res.end(JSON.stringify(obj ?? {}));
  };
  try {
    switch (u.pathname) {
      case "/targets":
        return reply(200, (await targets()).filter((t) => t.type === "page").map((t) => shape(t)));
      case "/info": {
        const t = await findTarget(tid);
        const ready = await withSession(t.webSocketDebuggerUrl, async (s) => {
          const r = await s("Runtime.evaluate", { expression: "document.readyState", returnByValue: true });
          return r?.result?.value === "complete";
        }).catch(() => null);
        return reply(200, shape(t, ready));
      }
      case "/new": {
        const url = (await readBody(req)).trim() || u.searchParams.get("url") || "about:blank";
        const created = await httpJson(`${CDP}/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
        return reply(200, shape(created));
      }
      case "/navigate": {
        const url = (await readBody(req)).trim() || u.searchParams.get("url");
        const t = await findTarget(tid);
        await withSession(t.webSocketDebuggerUrl, (s) => s("Page.navigate", { url }));
        return reply(200, shape(t));
      }
      case "/eval": {
        const js = (await readBody(req)).trim();
        const t = await findTarget(tid);
        const r = await withSession(t.webSocketDebuggerUrl, (s) =>
          s("Runtime.evaluate", { expression: js, returnByValue: true, awaitPromise: true }));
        return reply(200, { value: r?.result?.value ?? null, type: r?.result?.type ?? null });
      }
      case "/click": {
        const sel = (await readBody(req)).trim();
        const t = await findTarget(tid);
        const r = await withSession(t.webSocketDebuggerUrl, (s) =>
          s("Runtime.evaluate", {
            expression: `(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'not_found';el.click();return 'clicked';})()`,
            returnByValue: true,
          }));
        return reply(200, { value: r?.result?.value ?? null });
      }
      case "/scroll": {
        const dir = u.searchParams.get("direction") || "bottom";
        const t = await findTarget(tid);
        const expr = dir === "top" ? "window.scrollTo(0,0)"
          : dir === "bottom" ? "window.scrollTo(0,document.body.scrollHeight)"
          : `window.scrollBy(0,${Number(dir) || 500})`;
        const r = await withSession(t.webSocketDebuggerUrl, (s) =>
          s("Runtime.evaluate", { expression: expr, returnByValue: true }));
        return reply(200, { value: r?.result?.value ?? null });
      }
      case "/close": {
        const t = await findTarget(tid);
        return reply(200, { closed: t.id, result: await httpJson(`${CDP}/json/close/${t.id}`) });
      }
      default:
        return reply(404, { error: `no such endpoint: ${u.pathname}` });
    }
  } catch (e) {
    return reply(502, { error: String(e.message || e) });
  }
});

// Fail fast with a diagnosable message when the browser side is not up.
try {
  const v = await httpJson(`${CDP}/json/version`);
  console.log(`[proxy] CDP ok: ${v.Browser} @ ${CDP}`);
} catch (e) {
  console.error(`[proxy] cannot reach ${CDP} (${e.message}).`);
  console.error("[proxy] Start Chrome on a copied profile with --remote-debugging-port and --user-data-dir,");
  console.error("[proxy] or check `lsof -nP -iTCP:<port>` — a default-dir launch silently drops the flag.");
  process.exit(1);
}
server.listen(PORT, "127.0.0.1", () => console.log(`[proxy] listening on http://127.0.0.1:${PORT}`));
