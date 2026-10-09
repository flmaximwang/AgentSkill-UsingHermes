# PICO 5.09 / pico-class editors (Pine–Alpine lineage)

## Identity
- `pico -version` prints `Pico 5.09`; `pico -?` prints the full option table; the running screen's top line reads `UW PICO 5.09` + `File: <path>` + `Modified` when the buffer is dirty.
- Verify the banner before answering: on some distros `pico` is a symlink to GNU nano, and nano's bindings/flags differ (`-v` view, `M-G` goto, different `^T`). Real PICO 5.09 (Alpine composer build) has no `-v` in its option array.
- Bottom two lines of the screen are the live key menu; `^G` gives the same commands in full sentences, `^L` redraws a garbled screen.

## Key table (from the binary's own help text)
- `^G` help · `^O` WriteOut (save) · `^R` read/insert external file · `^X` exit
- `^K` cut (whole line, or the marked block) · `^U` UnCut (paste) · `^^` mark (Ctrl-^ = 0x1E, usually Ctrl-Shift-6) · `^D` delete char under cursor · `^H` backspace · `^I` tab
- `^W` Where is (search, case-insensitive) · `^J` format/justify current paragraph · `^T` spell check · `^C` report cursor position
- `^F/^B` char forward/back · `^P/^N` line up/down · `^A/^E` line start/end · `^V/^Y` page forward/back

## Prompt strings (verbatim, from the binary)
- Save: `File Name to write : ` with `T To Files`, `C Cancel`, `TAB Complete` on the line below; status flashes `[ Writing... ]` then `[ Wrote N line ]`.
- Exit with a dirty buffer: `Save modified buffer (ANSWERING "No" WILL DESTROY CHANGES) ?` with `Y Yes`, `C Cancel`, `N No`. Answering `N` exits and leaves the file on disk unchanged.
- Open: `[ Reading file ]` / `[ Read N line ]`. Search miss: `[ "foo" not found ]`. Mark: `[ Mark Set ]`. After `^J`: `[ Can now UnJustify! ]`.
- `^C` prints `[ line N of M (p%), character i of j (q%) ]` — use it to confirm a jump landed where you expected.

## Options (`pico -?`, condensed)
- `-e` file-name completion · `-k` `^K` cuts cursor->end-of-line instead of the whole line · `-a` show dot files · `-j` Goto in file browser · `-g` show cursor in browser · `-m` mouse · `-x` no key menu · `-z` allow `^Z` suspend · `-f` force function keys · `-d` delete key deletes under cursor · `-p` preserve `^Q`/`^S` · `-q` termcap/terminfo wins
- `-r[#cols]` fill column, default 72 · `-w` NoWrap ("allow editing of long lines") · `-W <wordseps>` · `-Q <quotestr>` · `-b` allow search and replace (off by default) · `-s <speller>` · `-t` shutdown mode · `-o <dir>` operating dir · `-n[#s]` mail notify · charset/color flags (`-dcs`, `-kcs`, `-syscs`, `-ncolors`, `-ntfc` …)

## Measured behavior (pty harness, 80x24, pico 5.09)
- `pico +N file` jumps to line N (verified via `^C`: `line 3 of 6`).
- Typing 119 chars on one line, no `^J`: the file keeps ONE line (119 cols) with both default settings and `-w` — typing does not hard-wrap.
- `^J` on that 119-char paragraph rewraps it to 2 lines, longest 72 cols — in BOTH default and `-w` mode. So `-w` does not protect against justify hard-wrapping; what exactly `-w` changes on screen was not pinned down (a 159-char line rendered identically in both modes) — say so rather than assert.
- `^W` then Enter repeats the previous search string.
- `^K` pastes back with `^U`; mark-then-move-then-`^K` cuts the marked region.
- The `^G` help text confirms paragraphs are delimited by blank lines or indentation — that is why justify can pull separately typed lines into one line.

## Answer traps to always include
- `^S` is not save (terminal flow control eats it, screen freezes; `^Q` unfreezes). Save is always `^O`.
- `^J` is justify, not newline: advising pico for config/long-line edits without warning about it destroys formatting silently.
- Stuck at a prompt: `^C` cancels the prompt, then `^X` quits; `^X` + `N` discards.
- Escape the tool permanently for git/crontab/visudo: `export EDITOR=nano` or `git config --global core.editor vim`.
