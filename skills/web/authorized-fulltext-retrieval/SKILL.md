---
name: authorized-fulltext-retrieval
description: "Use when a paywalled paper needs the user's browser login."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [fulltext, paywall, institutional-access, cdp, chrome, literature]
    related_skills: [blocked-page-recovery, zotero-mcp, web-content-extraction]
---

# Authorized full-text retrieval

Use when a document is **gated and the user is entitled to it** — a paywalled paper their institution
subscribes to, a vendor portal behind their account. The access comes from the session they are already
logged into, so no archive and no scraper can substitute for it. It also covers pulling a whole batch of
such documents once a download toolchain is wired up.

Companion skill: `blocked-page-recovery` owns the *anonymous* ladder (Wayback / archive.today / Jina /
API pivot) for pages that are **gone**. Route by which failure you actually have: gone → that skill;
gated-and-entitled → this one. Working the anonymous ladder on a paywalled paper burns turns for a copy
that cannot exist.

Nothing here bypasses a paywall, DRM, or 2FA. It reuses an entitlement the user already holds.

## When to Use

- A paper or report you were asked to obtain is gated, and the user has (or may have) institutional or
  account access to it.
- A fetch returned 403 / a login page / an anti-bot interstitial on a resource the user is entitled to —
  as opposed to a page that is simply gone.
- A batch of such documents has to be pulled and imported, rather than one file handed over by URL.
- Not for: pages that are deleted or never crawled → `blocked-page-recovery`; an open-access document →
  the OA probe alone finishes the job; wiring a login-walled *API* into an agent → `site-mcp-integration`.

## Non-negotiables

- **Probe the free routes before touching the browser.** One API call often deletes the whole branch.
- **Never type, ask for, or accept a credential or verification code.** Logins, QR, SMS/OTP, passkeys and
  CAPTCHA are the user's to complete. Clicking a visible login/confirm button once is allowed only with
  explicit authorization in that conversation, and never into a credential field.
- **Call the user for a bot wall instead of grinding on it.** This user asks to be called when a bot check
  appears. Attempt a visible checkbox/slider at most twice on one tab, confirm the challenge cleared, then
  hand the tab over and stop.
- **The user clears bot walls; the agent's only job is the download.** Handing over a challenged tab IS the
  mechanism — do not build bypass machinery for it. That makes a **visible** browser a precondition: a
  headless automation browser cannot be seen, so the handoff is impossible and every wait times out. Settle
  this *before* planning the handoff — `hermes config set browser.headed true`, then verify with
  `hermes config get browser.headed`, and kill any already-running browser process tree (an instance
  launched while the setting was false stays headless).
- **A batch must fail fast.** Drive it one item at a time and stop on the first item that is not
  successful; this user asked for it explicitly, because a batch that only reports at the end spends the
  whole run every time something breaks. Keep a per-item JSONL progress file plus a `--resume` that skips
  items already recorded successful, so a stop is a pause rather than a restart. On the stop, scan the open
  browser tabs for the challenge page and print its URL — that is the handoff the user needs.
- **Dispatch shape when the user asks for it: one fresh subagent per item, driven by a written prompt.**
  Fix the prompt once into a file (DOI, landing page, output path, the bot-wall wait-and-report rule, and an
  explicit ban on trying to solve the check), then reuse it per item. Two constraints shape that prompt,
  because a child is not a smaller you: a subagent **cannot ask the user a question**, so "hand the wall
  over" degrades to "wait a bounded time, then report where it stopped" — authorize the wait, cap it, and
  require the child to report the page title and URL on giving up; and the automation browser is one shared
  session, so a child will see the user's own tabs — tell it to leave them alone and to say what it observed
  rather than acting on them.
- **Judge a batch per item, never from the exit code or the summary.** Run the driver's per-item verdicts
  (`downloaded` / `pdf_fetch_failed` / `credentials_missing` / `verification_auto_failed` …) and report those;
  a run that fetched two of fourteen exits 0 and looks identical to one that fetched all fourteen.
- **A missing login session is not a missing entitlement.** A profile-less automation browser failing to
  see a full text says nothing about the user's subscription — get onto the profile that holds the session
  before drawing any conclusion.
- **Read the bytes, never the status line.** Report a download as successful only after the file exists at
  the expected size with a valid signature, or the manifest marks it downloaded. A toolchain's `ok` is a
  self-report.
- **A resolver-driven fetcher is only as legitimate as the user's resolver list.** Zotero's "Find Full Text"
  (and any CLI wrapper around it, e.g. `zot find-pdf`) executes whatever sits in
  `extensions.zotero.findPDFs.resolvers` in the Zotero profile `prefs.js` — including entries marked
  `"automatic": true`, which are used without further asking. Read that pref before invoking such a command:
  if it names a piracy mirror, stop and ask which route to take, because *running the command is what
  performs the fetch*. A `found: false` back from it means no resolver produced an entitled hit, not that
  the plumbing is broken.

## Procedure

1. **Probe OA** (Europe PMC, by DOI): `isOpenAccess` + `pmcid`, then `fullTextXML` for the OA subset. A
   publisher's "Open Access" badge is not the OA subset, and a 403 HTML body on a badge-carrying page is
   normal — probe, never promise. Recipe: `references/authorized-institutional-access.md` §1.
2. **Attach to the user's real Chrome**, not a fresh profile. Preconditions, the profile-copy recipe, and
   the trap where a debug port silently never opens: `references/authorized-institutional-access.md` §2.
3. **Stand up the CDP proxy** the download toolchains expect on `127.0.0.1:3456`:

   ```bash
   node scripts/local-cdp-proxy.mjs --port 3456 --cdp http://127.0.0.1:9222
   curl -s http://127.0.0.1:3456/targets      # must return page targets, not an error body
   ```

   Endpoint contract: `references/authorized-institutional-access.md` §3.
4. **Configure the institutional entry** the user actually lands on (a CARSI/Shibboleth IdP entry, an
   EZproxy, a resource portal) — not a school name. Confirm with the toolchain's own health check.
5. **Run the batch with the gates it enforces** — an explicit per-batch choice (`--si` / `--no-si`) asked
   once for the whole batch, and its `…_waiting_user` statuses treated as handoffs rather than failures.
6. **Import the results** into the reference manager. Do **not** assume its MCP can write: with the server in
   local-only mode every write tool — including the add-from-file one — returns
   `Cannot perform write operations in local-only mode`, and it does not fall through to the local HTTP API.
   Test a write before planning around it. Verified paths for a file already on disk, in preference order:
   `zot attach <item-key> --file <pdf> --via-bridge` (the `zot` CLI plus its `zot-cli-bridge` Zotero plugin —
   imports into local storage immediately, byte-exact and full-text indexed on arrival, no Web API key).
   The bridge is a **user-installed precondition**: `zot bridge install` only *builds* the `.xpi`, and modern
   Zotero refuses a sideloaded plugin, so hand the user the two steps (Tools → Plugins → gear → Install
   Plugin From File…, then restart Zotero) and wait for them. Confirm with `zot bridge status` or
   `curl -s 127.0.0.1:23119/zot-cli/ping` before planning any bridge-backed command around it —
   `bridge_missing` there means exactly that, not a permission problem.
   The desktop's local HTTP API is a real second route but is **split by operation**: creating items and
   filing them into a collection work (base is `/api/users/0/`, not `/api/`; the authorize call must be
   answered with "Always Allow" or the key is single-use; file into a collection by patching the item's
   `collections`, since `POST /collections/<key>/items` is 405), while **attaching a file body does not** —
   the upload applies and the bytes transfer, then registration is rejected, so send binaries through the
   bridge instead. Reading the resulting attachment's `links.enclosure` needs the `file://` scheme stripped
   before it is a usable path.

## Pitfalls

- **A debug port that is configured but not listening.** Chrome ignores `--remote-debugging-port` when the
  user-data-dir is the browser's **default** directory, and passing that same default path explicitly does
  not lift it. Chrome starts, `ps` shows the flag, nothing listens. Test with `lsof -nP -iTCP:<port>` —
  never by re-reading your own command line — and run the automation instance on a **copy** of the profile.
- **A running Chrome blocks real-profile attach.** Hermes' real-profile mode copies the profile, so a
  running Chrome's write locks on `Login Data` / `Web Data` make it refuse rather than risk losing logins.
  Quit Chrome first — and note this is the *opposite* requirement from reusing a live session, so pick one
  route deliberately instead of doing both.
- **Real-profile mode also needs the OS default browser to be a supported Chromium** (Chrome / Edge /
  Brave / Chromium). With Safari or Firefox as default it declines; set Chrome as the default for `https`,
  or take the manual profile-copy route.
- **Do not hunt for the upstream proxy.** The download-skill family expects a CDP proxy it does not ship
  and fails with "proxy not reachable" when it is absent. Implement it from the contract; it is ~150 lines
  of stdlib Node.
- **Don't report the plumbing as a result.** Getting the port up, the session restored and `/targets`
  answering is verified plumbing — not a downloaded paper. Keep the two claims separate in the report.
- **A batch's completion is not its success rate.** Read the run's own manifest and report per-item statuses
  (`downloaded` / `pdf_fetch_failed` / `credentials_missing` / `verification_auto_failed` / `no_authorized_pdf_found`)
  — the exit code is 0 either way, and a batch that fetched two of fourteen looks identical to one that
  fetched all fourteen until you count the files on disk.
- **A read-only reference-manager MCP is not a read-only reference manager.** The desktop's HTTP service can
  accept writes while the MCP refuses them, so "the MCP can't write" never means "hand-place the file" —
  switch to the local API or the `zot` CLI route.
- **Cloudflare decides on TLS fingerprint, so cookies do not carry the clearance.** Exporting the browser's
  full cookie jar for the host — `cf_clearance`, `__cf_bm` and all — and replaying it through `curl` still
  returns the 403 interstitial on a challenge-protected publisher. Never spend a turn on cookie export; the
  request has to originate from the browser body.
- **A freshly created tab is `readyState === "complete"` while still on `about:blank`.** Readiness polled on
  `readyState` alone reports success before navigation even starts, so every follow-up `eval` runs against a
  blank document (`location.origin` then reads back `null`). Gate on `location.href` containing the expected
  host **and** `readyState`, and poll rather than sleeping a fixed amount.
- **`Network.getResponseBody` on a PDF navigation returns the viewer's HTML, not the PDF.** A `200` with
  `content-type: application/pdf` is the navigation succeeding, and the body you read back is Chrome's
  embedder stub (~500 bytes) — it is not a truncated download. To get real bytes, make the browser *save*
  the file rather than render it (reference §6), and validate the `%PDF` magic before believing any capture.
- **`Network.getCookies` no longer exists on current Chrome.** Testing the fingerprint hypothesis by
  enumerating the jar returns `-32601` "wasn't found"; the surviving method is `Storage.getCookies`. The
  enumeration still reproduces the 403 — it demonstrates the mechanism, it does not change the outcome.
- **A PDF's page count from `file(1)` is a guess, not a fact.** Its summary line reports page counts that
  can differ sharply from reality, so a complete capture can read as truncated. Confirm with
  `mdls -name kMDItemNumberOfPages <pdf>` or by counting `/Type /Page` objects, and compare against the
  page range in the citation — never call an artifact truncated, or complete, on `file`'s word alone.
- **A download that fails instantly and identically for every host is an environment proxy, not the
  publisher.** Check `HTTP_PROXY` / `HTTPS_PROXY`, probe the port (`nc -z 127.0.0.1 <port>`; `curl -v`
  prints the proxy line it is using), and isolate it with `curl --noproxy '*'` before drawing any conclusion
  about the site — and before touching the browser route at all.
- **Do not rescue a blocked byte-fetch by rotating to a fresh tab per attempt.** Each new tab is a new
  challenge candidate; hammering one publisher across many tabs degrades every subsequent request to that
  host, including the landing page. Keep one article at a time on one tab, and stop when it goes bad.
- **Identify a downloaded file by its contents, never by its filename.** Files that come back from a shared
  download folder carry whatever abbreviations the user chose (`bai2016.pdf`, `zhu2021.pdf`), and those names
  lie often enough to file the wrong PDF: in practice two of a dozen pointed at a different paper than the
  name suggested, and one misleading name is enough to attach an unrelated document to an item. Extract the
  identity from the document itself — `pdftotext -f 1 -l 2 <pdf> -`, match
  `10\.\d{4,9}/[^\s"'<>()\[\]]+` against the target DOI, and when the DOI does not extract cleanly fall
  back to the volume/page line plus the title from page 1. Cross-check the page count against the cited page
  range (`pdfinfo`, or `mdls -name kMDItemNumberOfPages`) before calling a file complete or truncated — a
  file far larger than its neighbours is a whole-issue collation, and a genuinely long review is not.
- **Verify a filed attachment by hashing it, not by its size.** After an import, read back the library's own
  record (`GET /api/users/0/items/<attachment-key>/`) **and** hash the stored bytes
  (`~/Zotero/storage/<attachment-key>/` → `md5 -q`) against the source file. Equal size is not enough: a
  same-size, different-hash file is a different artifact (another compression batch, or a different PDF) and
  a size-only check passes it. Report success from the matched hash, never from the importer's `ok`.
- **An attachment field reading `null` is not evidence of a missing file.** Only *linked* attachments carry a
  path; imported ones keep their bytes under `~/Zotero/storage/<attachment-key>/` and report `path: null`
  forever. Judge presence from the storage directory (a non-hidden file of plausible size), never from that
  field — reading `null` as "empty placeholder" nearly reported a delivered paper as missing.
- **For a hand-built book / edited-volume item, take the ISBN from the copyright page, never the front
  matter.** The "Related Titles" page is an advertisement for *other* books and its multi-column layout
  scrambles the title↔ISBN pairing, so it yields an unrelated ISBN. The copyright page carries this book's
  Print / ePDF / ePub / oBook ISBNs and the publisher; take editor, place and year from there too, and
  cross-check the page count before writing `numPages`.
- **Audit the items' real holdings before and after an import batch.** "Has an attachment" is not "has full
  text", so count by a non-hidden file of real size per attachment directory, and re-run that count at the
  end — it is the only number that says how many items actually came out of the run with text.

## Answering "要我做什么"

When the remaining work needs input only the user can give, reply with a numbered list of **only those
items** — the values you need, the single consent, the one thing not to do while you work — followed by
one short block of what you will do yourself. A menu of options, or a restatement of the plan, is not an
answer to that question.

## Support files

- `references/authorized-institutional-access.md` — §1 OA probing; §2 attaching to the user's real Chrome
  (preconditions, the profile-copy recipe, the default-profile trap); §3 the CDP proxy endpoint contract
  and the toolchain gates; §4 the login/bot-check handoff; §5 what was and was not verified; §6 capturing
  real file bytes when a rendered capture is not enough.
- `scripts/local-cdp-proxy.mjs` — stdlib-only CDP proxy exposing that contract. Node 22+ (global
  `WebSocket`), zero dependencies, reads no cookies / passwords / localStorage.
- `scripts/failfast_batch.py` — generic fail-fast batch driver: one subprocess per item, per-item status
  read from that subprocess's own output, stop at the first item that is not successful, JSONL progress plus
  `--resume`. Use it to wrap any per-item fetch command; it is toolchain-agnostic on purpose.
