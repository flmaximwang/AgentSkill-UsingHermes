# GUI app settings: probing the installed copy (macOS)

Use when the user asks where a setting is, why they cannot find it, or how to change an app's look — the answer must come from the version installed on this machine.

## Probe order (stop as soon as the question is answered)
1. **Live config file.** Qt apps: `~/.config/<app>/<app>.ini` (macOS). Also check `~/Library/Application Support/<App>/`. It names the key and holds the current value (`[Start] style` / `styleName`, `[Viewer] backColor`, `[Browser] prevBackColor`). The file is rewritten by the running app — a value that moved between two reads is the user clicking, not a bad read.
2. **Bundled release notes.** `Contents/Resources/WhatsNew.txt` lists every version with one-line changes and links the vendor thread. Search it for the feature word: it tells you when a setting was added or relocated, e.g. a theme selector that only existed in the View menu until it was added to the settings window in a specific release.
3. **Widget names and ini keys inside the binary.**
   ```sh
   strings -a /Applications/<App>.app/Contents/MacOS/<App> > /tmp/app.txt
   grep -nE 'cb[A-Z]|<Section>/<key>|^Theme$' /tmp/app.txt
   ```
   Widget-name runs belong to one dialog class each; the settings dialog's ini keys (`Start/style`, `Start/styleName`, …) sit right beside its class name, which is how you prove which page owns a key. Universal binaries repeat every string twice (one copy per architecture) — two identical hits are one string.
4. **Literal UI labels from translations.** `Contents/Resources/language/<app>_<locale>.qm`. Do NOT hand-roll a QM section parser: this build's framing does not match the documented Qt layout (an extra language section, no separate Contexts block), so a from-scratch parser burns calls and yields zero messages. Read byte windows instead — English source strings and dialog-context names are stored as plain ASCII bytes, the translated label sits next to them as UTF-16BE:
   ```python
   d = open('/Applications/XnViewMP.app/Contents/Resources/language/xnview_zh_CN.qm','rb').read()
   i = d.find(b'Preview background color')          # plain ASCII source works
   seg = d[i-200:i+120].decode('utf-16-be','ignore')
   print(''.join(c if c.isprintable() else '·' for c in seg))
   # entry order in the stream: [local label][english source][dialog context]
   ```
   A run like `预览背景色 … Preview background color … SettingsBrowser` proves the Chinese item label AND the dialog class that owns it. If the source string is unknown, search a known CJK label instead (`'主题'.encode('utf-16-be')`). No Qt bindings needed; PyQt/PySide are usually absent anyway.
5. **Vendor tracker / forum.** The release-notes link resolves the definitive answer ("Settings>General>Theme", sourced from the app's author) and shows the version gate. Authoritative over any third-party blog.

## Answer shape for these questions
- Menu path in the UI's own language, with the English in parentheses: 工具 → 设置 → 常规 → 主题 (Tools → Settings → General → Theme).
- The version fact: since which release it is there, and where it used to be.
- The mechanism behind "I can't find it" (menu entry only rendered in one app mode; entry moved into the settings window in a later version).
- The neighbouring setting when the user's word is ambiguous, phrased as a decision rule ("if the UI is already light, what you see is the preview pane colour → that page"), not as a list of alternatives.

## Worked example: XnView MP 1.12.1 (macOS, zh_CN)
- Config: `~/.config/xnviewmp/xnview.ini`; `[Start] style` / `styleName` hold the theme, `[Viewer] backColor` / `fullBackColor` the image canvas, `[Browser] prevBackColor` the preview pane (dark grey by default — the surface a user usually calls "dark background"), `[Appearance] thumbBackColor` the thumbnail area.
- Whole UI theme: 工具(Tools) → 设置(Settings) → 常规(General) → 主题(Theme) — item list 默认/浅色/暗色/黑色 (Default/Light/Dark/Black). Also 查看(View) → 主题, but that entry only exists in browser mode; it is missing while a single image is open, which is the classic "I can't find the setting". The theme moved into the settings window in a release whose WhatNew line is `Theme in Settings`.
- Image canvas colour: 设置 → 查看(View) → 背景色. Preview pane colour: 设置 → 浏览器(Browser) → 预览背景色.
- Evidence trail: `xnview_zh_CN.qm` pairs 主题↔Theme with context `SettingsGeneral` and 预览背景色↔Preview background color with `SettingsBrowser`; the same binary also contains XnConvert's settings strings (`about_img_xnc.png`, "Add 'Convert with XnConvert' to context menu"), so a theme item list found next to those must be corroborated against XnView's own release notes before being taught.
