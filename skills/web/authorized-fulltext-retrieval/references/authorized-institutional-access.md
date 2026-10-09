# Authorized institutional access via the user's own browser

Depth for `authorized-fulltext-retrieval`. Use when the page is **gated and the user is entitled to it** —
a paywalled paper their institution subscribes to, a vendor portal behind their account.

Nothing here bypasses a paywall. The whole point is to reuse an entitlement the user already has.

## 1 — Probe the free routes first

One API call can delete the entire browser branch, so do it before anything else.

- **Europe PMC** is the OA status authority: search by DOI, read `isOpenAccess` and `pmcid`.

  ```bash
  curl -s --get "https://www.ebi.ac.uk/europepmc/webservices/rest/search" \
    --data-urlencode 'query=DOI:"10.xxxx/yyyy"' \
    --data-urlencode resultType=core --data-urlencode format=json --data-urlencode pageSize=1
  ```

  Then `https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML` for the OA subset. That
  endpoint answers `200` only for members of the subset; a `500` means "not in it", not "no free copy".
- **A publisher's "Open Access" badge is not the OA subset.** A PDF fetch returning 403/HTML on a page that
  advertises Open Access is normal; and an `isOpenAccess=N` record that still carries a PMC id is an author
  manuscript, not a free copy. **Probe before you promise** — never tell the user a paper is fetchable from
  a badge alone, and move anything unconfirmed into the download list.
- The legacy NCBI PMC OA service (`.../pmc/utils/oa/oa.fcgi`) is gone (404) — do not route through it.
- Probing a whole list is a loop, not a hand-check: collect the DOIs, then emit one row per item
  (`OA` flag, `pmcid`, title) so the user gets an OA / non-OA split as the deliverable.

## 2 — Attaching to the user's real Chrome

A profile-less / automation browser has no login state, so a failure there is **not** evidence of missing
entitlement. Get onto the profile that holds the session.

### Preconditions for Hermes' own real-profile mode

- The **OS default browser must be a supported Chromium** (Chrome / Edge / Brave / Chromium). With Safari
  or Firefox as default it declines outright — set Chrome as the macOS default for `https`, or take the
  manual route below.
- Chrome must be **fully quit**. Hermes copies the profile, and a running Chrome holds write locks on
  `Login Data` / `Login Data For Account` / `Web Data`; it aborts rather than risk losing committed logins.
  Verify with `pgrep -x "Google Chrome"`, then quit it.

### The Chrome ≥136 trap — why a debug port silently never opens

Chrome ignores `--remote-debugging-port` when the user-data-dir is the browser's **default directory**, and
passing `--user-data-dir` explicitly with that same default path does **not** lift the restriction. The
symptom is nasty: Chrome starts fine, `ps` shows the flag, and nothing ever listens. Confirm with
`lsof -nP -iTCP:9222` (empty = dropped) — never by re-reading your own command line.

The fix is to run the automation browser on a **copy** of the profile, which keeps the logins:

```bash
SRC="$HOME/Library/Application Support/Google/Chrome"
DST="$HOME/Tools/chrome-authctl"
ditto "$SRC" "$DST"                    # macOS-native copy; keeps Cookies + Local State
rm -f "$DST"/{SingletonLock,SingletonSocket,SingletonCookie,DevToolsActivePort}  # stale locks
open -na "Google Chrome" --args --user-data-dir="$DST" --remote-debugging-port=9222 --restore-last-session
for i in $(seq 1 25); do curl -s --max-time 2 http://127.0.0.1:9222/json/version && break; sleep 1; done
```

A Chrome profile is usually only a few hundred MB — check `du -sh` before deciding; the copy takes seconds
and saves every re-login. The user's normal Chrome keeps working: a different `--user-data-dir` is a
separate process, so they browse as usual while automation holds the copy. **Say so in the report** — their
cookies are in play, and a consent question later should be answerable.

Verify attachment, do not assume it: `curl -s http://127.0.0.1:9222/json/version` returns the browser
identity, and `curl -s http://127.0.0.1:9222/json/list` lists the restored page targets.

## 3 — The CDP proxy contract

Document-download toolchains (the `nature-downloader` family and similar skills) do **not** ship a proxy;
they expect one at `http://127.0.0.1:3456` speaking this contract, and fail with "proxy not reachable" when
it is missing. Implement it rather than hunting for the upstream skill:

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/targets` | — | `[{targetId,url,title,type}]` |
| GET | `/info?target=<id>` | — | `{targetId,url,title,ready}` |
| POST | `/new` | url | `{targetId,...}` |
| POST | `/navigate?target=<id>` | url | page shape |
| POST | `/eval?target=<id>` | JS | `{value}` |
| POST | `/click?target=<id>` | selector | `{value}` |
| GET | `/close?target=<id>` | — | `{closed}` |
| GET | `/scroll?target=<id>&direction=bottom` | — | `{value}` |

`../scripts/local-cdp-proxy.mjs` implements it in stdlib Node (global `WebSocket`, 22+), zero deps, and
touches no cookie / password / localStorage. Start it, then confirm with
`curl -s http://127.0.0.1:3456/targets` — an error body here is the same failure the toolchain will report.

### Gates the toolchain itself enforces

- **Supporting information is an explicit per-batch choice.** The downloader returns
  `si_confirmation_required` and creates nothing unless given exactly one of `--si` / `--no-si`. Ask it
  **once for the whole batch, before the first run** — discovering it mid-batch costs a relaunch.
- **An institutional entry URL, not a school name.** Where the user authenticates through a federation,
  save the entry they actually land on; a CARSI/Shibboleth entry reports a health line such as
  `[CARSI] 入口可达，检测到特征：idp`. Ask for the login page they actually use when none is offered.
- **Its status vocabulary is a handoff vocabulary, not a failure list:** `carsi_waiting_user`,
  `publisher_verification_waiting_user`, `verification_auto_failed`, `sciencedirect_robot_check` all mean
  "a human is needed on a specific tab" — name the tab, keep it open, do not silently retry.
- **Publisher anti-bot pages are not login confirmations.** Keep one article at a time on sensitive
  publishers, reuse the same tab after the user clears a check, and never open many publisher tabs in
  parallel.

## 4 — Login and bot-check handoff

- Leave the challenged tab open and name it; the user completes login, QR, OTP or the CAPTCHA there.
- This user asks to be **called when a bot wall appears** rather than have the agent grind on it. Attempt a
  visible checkbox/slider at most twice on one tab, verify the challenge cleared, then hand over.
- Never ask for, accept, or type a credential or verification code into a chat or a shell.
- When the user completes a step, continue from that same tab instead of opening a fresh one.

## 5 — What is verified here, and what is not

The attachment plumbing is verified by probe: the debug port comes up on the copied profile, the session
restores, and `/targets` answers through the proxy. Also verified by probe, and worth not re-deriving:

- A challenge-protected publisher returns the 403 interstitial to `curl` **even when the request carries the
  browser's complete cookie jar for that host** (including `cf_clearance` and `__cf_bm`). Fingerprint-based,
  not cookie-based — stop looking for the missing cookie. Enumerating the jar to prove that: on current
  Chrome `Network.getCookies` answers `-32601 wasn't found` and the working call is `Storage.getCookies`.
- Capturing a PDF through the CDP **Fetch** domain (response stage) does return a genuine response body, but
  re-issuing the request that way loses the clearance and the capture is the 403 interstitial, not the file.
- `Network.getResponseBody` on the PDF *navigation* returns the PDF-embedder HTML, whatever the reported
  `content-type` says.

**End-to-end retrieval of a paywalled PDF was still not verified** at the time of writing: the route below
is the one to take, not a proven result. Treat the plumbing as proven and the retrieval as untested, and
never report a download as successful from a status line — read the manifest and the bytes.

## 6 — Getting real bytes instead of a rendered capture

When the page is reachable in the browser but every programmatic capture returns the viewer stub, stop
capturing and make the browser **save** the file:

1. **Turn off the inline viewer** for the automation profile. Set `plugins.always_open_pdf_externally: true`
   in the profile's `Default/Preferences` JSON (back the file up first; also worth setting
   `download.default_directory` and `download.prompt_for_download: false` there). Chrome must be **relaunched**
   for a `Preferences` edit to take — and edit the profile *copy* the automation instance actually uses, not
   the user's source profile.
2. **Point downloads at a scratch directory** over CDP:
   `Browser.setDownloadBehavior {behavior: "allow", downloadPath: <dir>, eventsEnabled: true}`. Confirm the
   call returned an empty result rather than an error body.
3. **Navigate to the PDF URL, then poll the directory** for a new non-`.crdownload` file; wait for its size
   to settle, then move it into place and check the `%PDF` magic and the size floor.
4. A `download`-attributed `<a>` click is *not* a substitute — on a publisher serving the PDF `inline` the
   click either opens the viewer or is swallowed, and nothing lands in the directory.

The same shaped lesson applies to the first hop: resolve the landing page, read the PDF link out of the DOM
(`meta[name="citation_pdf_url"]` first, then anchors whose href or text says PDF), and only then fetch —
blindly requesting the article's `.pdf` path triggers a fresh challenge that a warm tab would have absorbed.
