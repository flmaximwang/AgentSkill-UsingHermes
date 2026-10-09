# Local-model memory providers: install, provision, verify, inspect

Scope: any Hermes memory provider that **ships its own model files** (an ONNX embedder, an NLI
cross-encoder) and stores facts in a local file. Covers getting its model files in place, proving
they are the pinned bytes, and reading the store back. Symptoms that lead here: the first
`remember()` dies with a missing-file or ONNX deserialize error, or the provider reports
"embedding generation failed" while the files look present.

One external provider is active at a time (`memory.provider`), always **alongside** the built-in
MEMORY.md/USER.md, and a config change takes effect only in a new session / restarted gateway.

## 1. Install and activate — per profile

```bash
hermes plugins info <name>        # read the disclosure first: model size, cache dir, licence
hermes plugins install <name>
hermes memory setup               # or: hermes config set memory.provider <name>
hermes memory status              # active provider + installed providers
```

Plugin discovery root is `$HERMES_HOME/plugins/` — **per profile**, exactly like `skills/`. The
docs' `User | ~/.hermes/plugins/` row reads like a global directory; it is the *default* profile's
own home, so another profile sees nothing until it is installed there too
(`hermes -p <profile> plugins install <name>`). Model caches live **outside** `$HERMES_HOME`
(`~/.cache/<plugin>/`), so a second profile re-downloads nothing; the store itself is per profile.

## 2. Read the pin table before touching any file

The plugin publishes what it expects: a pin table (model id + immutable revision + per-file hash)
and a loader that names the cache dir and the filenames it looks for. Note the flat layout — HF path
`onnx/model.onnx` lands as `<cache_dir>/model.onnx`, so `model.onnx_data` sits beside it.

**Pitfall — pre-placing the headline files bypasses the plugin's entire download routine.** The
loader is guarded as `if not exists(big1) or not exists(big2): download_all()`, so once the two big
ONNX files are in place the sibling files (`tokenizer.json`, `config.json`,
`special_tokens_map.json`, `sentencepiece.bpe.model`) are never fetched and first use dies at
`Tokenizer.from_file` with a missing file. Fetch **every** file the pin table lists, not just the
large ones.

**Pitfall — verify with the consumer's algorithm, not a generic one.** Pin hashes are mixed: LFS
files are pinned as the **plain sha256 of the file content**, and only `sha1:`-prefixed pins are
git-blob oids, `sha1("blob <len>\0" + content)`. Framing an LFS file with the blob header reports a
mismatch on a good file, and a repair driven by that verdict deletes or overwrites good data.
Recognize it by the pattern: *every* sha256-pinned file "fails" while sha1-pinned ones pass.

```python
def check(path, expect):                  # expect straight out of the plugin's pin table
    import hashlib, os
    if expect.startswith("sha1:"):
        h = hashlib.sha1(); h.update(b"blob %d\0" % os.path.getsize(path)); pre = "sha1:"
    else:
        h, pre = hashlib.sha256(), ""
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return pre + h.hexdigest() == expect
```

Run this over **every** pinned file and print `size / computed / expected / verdict` per file
before repairing anything, so the repair decision is evidence rather than inference. Never mix
verify-and-repair into one pass that can delete on a false verdict — verify first, then repair only
what actually fails.

## 3. Fetch GB-scale files over a flaky link (parallel ranges)

A plugin's own `urlretrieve`-style downloader has **no resume**: it deletes the temp file on failure
and restarts from zero, so a link that drops mid-transfer never finishes a multi-GB file. Measured
on a Chinese network: single-stream from `huggingface.co` ran ~0.3–0.4 MB/s and died around 100 MB.
N parallel range requests, each retried until its slice is complete and then concatenated, ran
~5–10× faster (~1.7–4.7 MB/s aggregate with 6 slices).

```bash
# total = last content-length from: curl -sIL "$url" | grep -i '^content-length' | tail -1
# for slice i of n: start=$((i*chunk)), end=min((i+1)*chunk-1, total-1)
curl -sS -L --retry 30 --retry-all-errors --retry-delay 3 \
     -r "$start-$end" -o "$dest.slice$i" "$url"
# then: retry any short slice (resume inside it with -r "$have-$end"), cat slices > dest,
#       and only then verify the whole-file hash
```

Pick the base URL that serves the pinned revision and **re-verify byte-for-byte against the pin** —
never assume a mirror serves the pinned revision just because the path resolves. A hash-mismatched
big file is worse than a missing one: the loader will trust its presence.

## 4. Restart the process before judging whether it works

A long-running gateway that tried to load the model while a file was missing or partial keeps a
**half-initialized** embedder and does not re-initialize in-process. Tell-tale in
`$HERMES_HOME/logs/gateway.error.log`, while a fresh CLI process against the same files works fine:

```
<plugin>: embedding generation failed: 'NoneType' object has no attribute 'encode'
Tool remember returned error: {"error": "Embedding generation failed"}
```

So the order is: provision → verify → **restart** (`/restart`, or wait for a new session) → test.
Do not restart the gateway from inside the session it serves: the restart kills delivery of the
turn that ordered it. Hand the user the command instead.

## 5. Acceptance test — write, read back, delete (fresh CLI process)

Models load per process, so a CLI call is the cheapest end-to-end test and touches no live session.

```bash
hermes <plugin> status                              # health, provider, total facts
hermes <plugin> seed --user <id> --content "<a realistic full sentence>"
sqlite3 -header -column "file:$HERMES_HOME/<plugin>.db?mode=ro" \
  "select fact_id,user_id,round(trust_score,3),retrieval_count,length(content) from facts;"
hermes <plugin> export --user <id>                   # read the record back
hermes <plugin> forget-fact <fact_id> --user <id>    # leave no test junk
```

- `mode=ro` in the SQLite URI keeps the probe from taking the provider's write lock.
- Some providers gate writes on length (both a character and a word minimum) and answer
  `rejected_fragment` to a short one-liner — smoke-test with a realistic full sentence.
- `hermes <plugin> …` takes `--hermes-home` to inspect another profile's store; `hermes -p
  <profile> memory status` shows that profile's provider.
- A `status`/`stats` reading of `0 facts` is not proof of a broken install — it is proof nothing
  was written yet. Distinguish "no data" from "cannot write" with the seed above.

## 6. `user_id` is the platform id in gateway sessions

In a Discord/Telegram session the provider is initialized with the **platform id** (snowflake /
uid) as `user_id`; a CLI call defaults to a generic id (`general`). Facts therefore land in
different buckets, and `export --user general` shows nothing after a session wrote facts. Log line:
`<plugin>: user <id> not in users.yaml (N known users) — attributing to raw ID`. Either pass the
platform id to `export`, or configure the provider's user manifest (`users.yaml`) to map it to a
name. **A correct manifest is not sufficient, though** — the manifest only helps the resolution call
sites that actually receive the platform, so check the provider's **per-turn** entry point (the one
`remember` / `sync_turn` / `prefetch` all route through) passes it; otherwise the bucket stays the
raw platform id no matter how right `users.yaml` is. Symptom that tells them apart: the prefetch
header shows the canonical display name (session-init resolved it) while the store's `user_id` is
still the snowflake. Diagnosis + fix + the old-rows migration: `use-limbic` §3
(`scripts/probe-identity-attribution.py`).
