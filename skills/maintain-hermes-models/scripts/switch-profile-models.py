#!/usr/bin/env python3
"""把某个 / 所有 profile 的默认模型指向同一个目标（只重写 `model:` 块体，幂等，可 --dry-run）。

改的是每份 config.yaml **顶层 `model:` 块的块体**：`model:` 头行原地保留，只换它下面的
default / provider / base_url / api_mode 四行。profile 不继承主 home 的 `providers:` 段，所以
该 profile 没有 `providers.<provider>:` 时，把主 home 里那一整块原样复制进去；主 home 自己也没有
这一段（内置 provider，凭证走 `.env`）时就不注入，只改 `model:` 块。

写之前跑三道自检（任一不过即非零退出、不留半成品）：
  1. 顶层键不得重复 —— 重复的 `model:` 会让严格加载器拒收整份文件，并**静默**回落到 last-good
     （症状是 `hermes profile list` 的 Model 列变成 `--`）。PyYAML 的 safe_load 不报这个错，
     所以判据是「顶层键计数」，不是「能不能解析」。
  2. 写后逐键核对 `model:` 块 == 目标值，且 `providers.<provider>:` 确实在文件里。
  3. 每个被写的文件先整份备份到 `<home>/backups/model-switch-<ts>/<label>/config.yaml`。

只用标准库：本机前台与后台 shell 解析到的 `python3` 可能不是同一个，第三方包（PyYAML）不能假设存在。

退出码：0 全部就绪（含「本来就在目标上」）· 1 有失败项 · 2 没有匹配到任何 profile。
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def top_keys(lines: list[str]) -> list[str]:
    return [m.group(1) for line in lines if (m := TOP_KEY.match(line))]


def dup_top_keys(lines: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    for key in top_keys(lines):
        seen[key] = seen.get(key, 0) + 1
    return sorted(k for k, n in seen.items() if n > 1)


def block_end(lines: list[str], start: int) -> int:
    """第一个缩进回到列 0 的实义行的下标 = 该顶层块的结束位置。"""
    for i in range(start + 1, len(lines)):
        if lines[i].strip() and TOP_KEY.match(lines[i]):
            return i
    return len(lines)


def parse_flat(lines: list[str]) -> dict[str, str]:
    """把一个块体解析成 {key: value}（这些块都是平铺的 key: value，不需要 YAML）。"""
    out: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.strip().partition(":")
        if not sep:
            continue
        out[key.strip()] = value.strip().strip("'\"")
    return out


def provider_block(main_lines: list[str], provider: str) -> tuple[list[str], list[str]]:
    """从主 home 的 config.yaml 取 `providers.<provider>:` 子树，还原成一段可插入的 `providers:` 块。

    返回 `(带 providers: 头的整块, 只有子块的片段)`：目标文件**没有**顶层 `providers:` 时插前者，
    **已有**时只把后者插进那个块的块尾 —— 否则会写出第二个顶层 `providers:`（重复顶层键）。

    主 home 里没有这一段时**返回两个空表**，不报错：那是**内置 provider**（deepseek / openai / anthropic /
    gemini …，凭证走 `<home>/.env` 的 `<NAME>_API_KEY`，profile 自己有 .env 就能解析），本来就不需要
    `providers:` 块；只有本机自定义名字的 provider（如快照里的 `volcengine-agent-plan`）才必须复制。
    """
    start = next((i for i, l in enumerate(main_lines) if l.rstrip() == "providers:"), None)
    if start is None:
        return [], []
    sub = next((i for i in range(start + 1, len(main_lines))
                if main_lines[i].rstrip() == "  %s:" % provider), None)
    if sub is None:
        return [], []
    end = len(main_lines)
    for i in range(sub + 1, len(main_lines)):
        line = main_lines[i]
        if line.strip() and not line.startswith("    "):
            end = i
            break
    return ["providers:\n"] + main_lines[sub:end], main_lines[sub:end]


def selftest() -> int:
    """合成两份 config 片段自检 provider_block 的返参形状与「不造重复顶层键」。

    返参形状与调用点漂开过一次（内置 provider 的两条早退路径 `return []`、调用点却解包两个值 ⇒
    ValueError），所以这里断言的是**结构**，不是文本：内置 provider 必须返回两个空表。
    """
    checks = []
    builtin = ["model:\n", "  default: x\n", "agent:\n"]
    got = provider_block(builtin, "deepseek")
    checks.append(("内置 provider → 两个空表", got == ([], [])))

    main_cfg = ["model:\n", "  default: x\n", "providers:\n",
                "  volcengine:\n", "    api_key: k\n", "    base_url: https://x/v1\n",
                "agent:\n", "  x: 1\n"]
    whole, sub = provider_block(main_cfg, "volcengine")
    checks.append(("自定义 provider → 整块带头、子块无头",
                   whole[:1] == ["providers:\n"] and sub[:1] == ["  volcengine:\n"]
                   and len(whole) == len(sub) + 1))
    checks.append(("子块只到下一个 4 空格缩进前", sub[-1].startswith("    base_url")))

    dup = dup_top_keys(["model:\n", "providers:\n", "providers:\n"])
    checks.append(("重复顶层键抓得住", dup == ["providers"]))

    bad = 0
    for name, ok in checks:
        print("%s %s" % ("ok  " if ok else "FAIL", name))
        bad += 0 if ok else 1
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="把某个/所有 profile 的默认模型指向同一个目标",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--home", default="~/.hermes", help="Hermes home（所有 profile 的家）")
    ap.add_argument("--model", help="目标模型 id（如 deepseek-v4-1-flash）")
    ap.add_argument("--provider", help="provider 名，不带 `custom:` 前缀")
    ap.add_argument("--base-url", default="", help="该 provider 的 base_url")
    ap.add_argument("--api-mode", default="chat_completions", help="留空则不动这一行")
    ap.add_argument("--profiles", default="all", help="`all`、`default` 或逗号分隔的 profile 名")
    ap.add_argument("--dry-run", action="store_true", help="只报会改什么，不落盘")
    ap.add_argument("--selftest", action="store_true", help="只跑自带的结构自检，不读任何 config")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.model or not args.provider:
        ap.error("--model / --provider 是必填（除非 --selftest）")

    home = Path(args.home).expanduser()
    main_cfg = home / "config.yaml"
    if not main_cfg.is_file():
        print("找不到 %s" % main_cfg, file=sys.stderr)
        return 2
    main_lines = main_cfg.read_text(encoding="utf-8").splitlines(keepends=True)
    provider_lines, provider_sub = provider_block(main_lines, args.provider)

    if args.profiles == "all":
        targets = [main_cfg] + sorted((home / "profiles").glob("*/config.yaml"))
    else:
        wanted = [w.strip() for w in args.profiles.split(",") if w.strip()]
        targets = [(main_cfg if w == "default" else home / "profiles" / w / "config.yaml") for w in wanted]
    if not targets:
        print("没有匹配到任何 profile", file=sys.stderr)
        return 2

    body = ["  default: %s\n" % args.model, "  provider: %s\n" % args.provider]
    if args.base_url:
        body.append("  base_url: %s\n" % args.base_url)
    if args.api_mode:
        body.append("  api_mode: %s\n" % args.api_mode)

    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = home / "backups" / ("model-switch-%s" % stamp)
    changed: list[tuple[str, bool]] = []
    already: list[str] = []
    failed: list[tuple[str, str]] = []

    for path in targets:
        label = "default" if path.parent == home else path.parent.name
        if not path.is_file():
            failed.append((label, "没有这份 config.yaml"))
            continue
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines(keepends=True)

        dups = dup_top_keys(lines)
        if dups:
            failed.append((label, "顶层键重复：%s（先修它，别在坏文件上继续写）" % ", ".join(dups)))
            continue
        if not lines or lines[0].rstrip() != "model:":
            failed.append((label, "第一行不是顶层 `model:`，形状不认识"))
            continue

        end = block_end(lines, 0)
        current = parse_flat(lines[1:end])
        current_provider = current.get("provider", "").replace("custom:", "").strip()
        if current.get("default") == args.model and current_provider == args.provider:
            already.append(label)
            continue

        adds_provider = bool(provider_lines) and not re.search(
            r"^  %s:" % re.escape(args.provider), raw, re.M)
        new_lines = list(lines)
        new_lines[1:end] = body
        if adds_provider:
            # 已有顶层 `providers:`（profile 普遍带着 volcengine 那一段）⇒ 只往块尾插子块，别再写一个头。
            prov_at = next((i for i, l in enumerate(new_lines) if l.rstrip() == "providers:"), None)
            at, chunk = (1 + len(body), provider_lines) if prov_at is None else \
                (block_end(new_lines, prov_at), provider_sub)
            new_lines[at:at] = chunk
        text = "".join(new_lines)

        after_dups = dup_top_keys(new_lines)
        if after_dups:
            failed.append((label, "写后顶层键重复：%s" % ", ".join(after_dups)))
            continue
        parsed = parse_flat(new_lines[1:1 + len(body)])
        if parsed.get("default") != args.model or parsed.get("provider") != args.provider:
            failed.append((label, "写后 model 块与目标不符：%s" % parsed))
            continue
        if adds_provider and not re.search(r"^  %s:" % re.escape(args.provider), text, re.M):
            failed.append((label, "providers.%s 没能插进去" % args.provider))
            continue

        changed.append((label, adds_provider))
        if args.dry_run:
            continue
        (backup / label).mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / label / "config.yaml")
        path.write_text(text, encoding="utf-8")

    print("home      : %s" % home)
    if not provider_lines:
        print("note      : 主 home 没定义 providers.%s —— 按内置 provider 处理（凭证走 <home>/.env 的"
              " <NAME>_API_KEY），不注入 `providers:` 块" % args.provider)
    print("backup    : %s%s" % (backup, "  [--dry-run：一个字节都没写]" if args.dry_run else ""))
    print("changed   : %d  %s" % (len(changed),
                                  ", ".join(l + (" +providers" if p else "") for l, p in changed) or "-"))
    print("already   : %d  %s" % (len(already), ", ".join(already) or "-"))
    for label, why in failed:
        print("  ! %s: %s" % (label, why))
    print()
    print("回读三件：")
    print("  1) hermes profile list                      # Model 列应全是 %s" % args.model)
    print("  2) hermes config check                      # 不该报 formatting error")
    print("  3) python3 scripts/verify-profile-models.py --expect-model %s%s"
          % (args.model, (" --expect-base-url %s" % args.base_url) if args.base_url else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
