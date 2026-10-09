# Vetting a hub candidate before installing it

A search hit is a sales page. Three gates decide whether the skill CAN be
installed, and a fourth decides whether it is worth installing. Run them in
order; each is cheap and each kills a candidate early.

## Gate 1 — can it be fetched at all?

Metadata and content travel on different calls. The catalog feed and the hub
search endpoint render a row from metadata the fetch never needed, so a candidate
can be visible and `inspect`-able while `fetch` returns `None`.

Tell: `hermes skills inspect <identifier>` prints the metadata panel with NO
`SKILL.md Preview` under it. Known cause: ClawHub refuses an ambiguous slug —
`GET https://clawhub.ai/api/v1/skills/<slug>` → `409 Conflict`, so
`ClawHubSource._skill_detail()` returns `None` and `fetch()` gives up.

Probe the fetch directly with the tree's own interpreter (`cwd` so `tools`
imports; `env -u PYTHONPATH` so the session's tree does not shadow it):

```bash
cd ~/.hermes/hermes-agent
env -u PYTHONPATH HERMES_HOME="$HERMES_HOME" venv/bin/python3 - <<'PY'
from tools.skills_hub_clawhub import ClawHubSource
s = ClawHubSource()
for ident in ("clawhub/<a>", "clawhub/<b>"):
    b = s.fetch(ident)
    print(ident, "->", None if not b else (b.name, b.identifier, sorted(b.files)))
    if b:
        print((b.files.get("SKILL.md") or "")[:1500])
PY
```

Read the bundle BEFORE installing it, not after: `sorted(b.files)` shows whether
the support files are sane, and the SKILL.md head shows whether frontmatter
exists at all — a skill with no `name`/`description` installs fine and then
renders as a blank row in `hermes skills list` and in the desktop list.

## Gate 2 — does the scanner allow it?

The install prints a verdict and a decision. The tiers do NOT behave the same:

| Verdict | Decision line | `--force` |
|---|---|---|
| clean / findings below the block threshold | `ALLOWED — Allowed (…, safe verdict)` | n/a |
| blocked on a community/caution source | `BLOCKED — Blocked (community source + caution verdict, N findings)` | clears it |
| `DANGEROUS` | `BLOCKED — Blocked (community source + dangerous verdict, N findings)` + `--force does not override a dangerous verdict` | **no effect** |

So `--force` is not a universal "install anyway". Expect the hard block from
rules like `curl_pipe_shell` (`curl … | sh` in an install snippet) and
`other_agent_config_ref` (the skill writes into another agent's settings file) —
both are common in skills whose whole job is wrapping a CLI. Report the finding
verbatim with its `file:line` and stop; the remedy is the author's, not the
user's, and no local flag buys past it.

Findings carry `pattern_id`, `severity`, `category`, `file`, `line`, `match`.
Scans are cached under `<skills>/.hub/scan-cache/` and recorded per item in
`.hub/lock.json` → `scan_provenance` (bundle hash, scanner version, verdict,
rules, `fresh`).

## Gate 3 — is the candidate the real thing?

- **Wrapper of a wrapper.** A skill whose content is "run this package through a
  helper script I wrote" adds a hop, not a capability. If the upstream tool has
  its own agent integration (an MCP server, an `install --target=<agent>` flow),
  install that and skip the skill entirely.
- **Version drift in the content.** Tool tables, flag lists and command examples
  describe SOME version of the tool. Verify the load-bearing claim against the
  binary (`<tool> --help`, or a live protocol probe) and report the difference
  rather than repeating the skill's numbers.
- **Commands that were never run.** A command that is not a real CLI surface
  (a subcommand belonging to a different, separately-installed binary; a flag the
  tool does not have) means the procedure section was authored from memory. One
  such command disqualifies the whole section.

## Survey recipe ("which hub skill does X?")

Enumerate and vet in one pass instead of installing the first plausible hit:

1. `hermes skills search <topic>` — collect EVERY candidate identifier, including
   the ones whose name does not match the description.
2. `hermes skills inspect <identifier>` per candidate → metadata + the resolved
   `Identifier:`; a missing SKILL.md preview is a Gate-1 failure.
3. The `fetch()` probe above for each survivor → real file list + content.
4. Only then install. Name the rejected candidates and the reason — the survey is
   what the user asked for, and it is worth more than successfully installing the
   wrong skill.

## Cost note

Leave DEBUG logging OFF for these probes. `logging.basicConfig(level=DEBUG)` on
the hub HTTP client prints every hop of every paginated listing (megabytes of
`httpcore`/`httpx` trace) and the probe dies on the command timeout before it
prints its own result. The one line that matters (`409 Conflict`) is already in
an INFO-level record.
