#!/usr/bin/env python3
"""limbic 模型文件：按插件自己的 pin 逐个校验，坏的/缺的补齐。

为什么需要它（实测 2026-10-09 · limbic 0.5.1 · macOS arm64）：
  * plugins/limbic/embeddings.py:_ensure_model 只在 model.onnx / model.onnx_data
    缺失时才调 _download_model() —— 手动预置这两个大文件会让同目录的
    tokenizer.json / config.json / sentencepiece.bpe.model 永远不被拉，
    症状是 Tokenizer.from_file 报 "No such file or directory (os error 2)"。
  * 它自己的下载器不支持断点续传（_urlretrieve_atomic 失败即删临时文件），
    国内单流实测 0.28-0.31 MB/s 且会在 100 MB~1.5 GB 处断，2.11 GiB 那份装不完。
  * pin 的哈希规矩：LFS 文件 = 文件内容原文的 sha256；
    只有 "sha1:" 开头的才是 git-blob（"blob <size>\\0" 前缀再 sha1）。
    把 LFS 文件也套 git-blob 头去比，会把完好的文件判成坏的并截断（踩过）。

用法：
  python3 -B fetch-pinned-models.py                    # 只校验并报告
  python3 -B fetch-pinned-models.py --repair           # 校验 + 补齐
  python3 -B fetch-pinned-models.py --repair --slices 6 --source https://huggingface.co
退出码：0 全部对上；1 有文件仍需修复（未加 --repair）或补齐后仍不对；2 找不到插件/无法读 pin。
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import subprocess
import sys
import time

# 插件里 OnnxEmbedder._default_cache_dir() / NliClassifier._default_cache_dir() 的落点。
SUBDIR = {}  # 由 load_pins() 填：model_id -> 缓存子目录名
PARALLEL_MIN = 100_000_000   # 超过这个字节数才值得并行分段
CHUNK = 1 << 22


def load_pins(plugin_dir: str):
    """从插件的 model_pins.py 读 pin 表；模型 id -> (revision, {相对路径: 期望哈希})。"""
    if not os.path.isfile(os.path.join(plugin_dir, "model_pins.py")):
        print(f"找不到 {plugin_dir}/model_pins.py —— 用 --plugin-dir 指到已安装的 limbic 插件目录",
              file=sys.stderr)
        raise SystemExit(2)
    sys.path.insert(0, plugin_dir)
    try:
        import model_pins as mp
    except Exception as exc:                                    # pragma: no cover
        print(f"读不了 model_pins.py：{exc}", file=sys.stderr)
        raise SystemExit(2)
    pairs = [(mp.EMBEDDING_MODEL_ID, "embedding"), (mp.NLI_MODEL_ID, "nli")]
    pins = {}
    for mid, sub in pairs:
        SUBDIR[mid] = sub
        pin = mp.model_pin(mid)
        pins[mid] = (pin["revision"], dict(pin["files"]))
    return pins


def digest(path: str, expect: str) -> str:
    """按 pin 的规矩算哈希：sha1: 前缀 = git-blob，其余 = 内容原文 sha256。"""
    if expect.startswith("sha1:"):
        h = hashlib.sha1()
        h.update(b"blob %d\0" % os.path.getsize(path))
        prefix = "sha1:"
    else:
        h, prefix = hashlib.sha256(), ""
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return prefix + h.hexdigest()


def check(path: str, expect: str):
    if not os.path.isfile(path):
        return False, "missing", 0
    return digest(path, expect) == expect, digest(path, expect), os.path.getsize(path)


def remote_size(url: str) -> int:
    out = subprocess.run(["curl", "-sIL", url], capture_output=True, text=True).stdout
    lens = [ln.split(":", 1)[1].strip() for ln in out.splitlines()
            if ln.lower().startswith("content-length")]
    return int(lens[-1]) if lens else 0


def fetch_single(url: str, dest: str) -> None:
    subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "30", "--retry-all-errors",
                    "--retry-delay", "3", "-o", dest, url], check=True)


def fetch_slices(url: str, dest: str, total: int, n: int) -> None:
    """n 路并行分段，每段重试到自己那一段完整为止，再拼回一个文件。"""
    chunk = math.ceil(total / n)
    parts = []
    for i in range(n):
        start, end = i * chunk, min((i + 1) * chunk - 1, total - 1)
        part = f"{dest}.slice{i:02d}"
        parts.append((part, start, end))
    procs = [subprocess.Popen(
        ["curl", "-sS", "-L", "--retry", "30", "--retry-all-errors", "--retry-delay", "3",
         "-r", f"{start}-{end}", "-o", part, url], stderr=subprocess.DEVNULL)
        for part, start, end in parts]
    for proc in procs:
        proc.wait()
    for part, start, end in parts:
        want = end - start + 1
        have = os.path.getsize(part) if os.path.exists(part) else 0
        tries = 0
        while have < want and tries < 40:
            tries += 1
            print(f"    续传 {os.path.basename(part)} 从 {start + have}", flush=True)
            subprocess.run(["curl", "-sS", "-L", "--retry", "30", "--retry-all-errors",
                            "-r", f"{start + have}-{end}", "-o", part, url],
                           stderr=subprocess.DEVNULL)
            have = os.path.getsize(part) if os.path.exists(part) else 0
        if have != want:
            raise SystemExit(f"{part} 仍未取全（{have}/{want}）")
    with open(dest, "wb") as out:
        for part, _, _ in parts:
            with open(part, "rb") as fh:
                for block in iter(lambda: fh.read(CHUNK), b""):
                    out.write(block)
            os.remove(part)


def main() -> int:
    home = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    ap = argparse.ArgumentParser(description="校验/补齐 limbic 的模型文件（按插件自己的 pin）")
    ap.add_argument("--plugin-dir", default=os.path.join(home, "plugins", "limbic"),
                    help="已安装的 limbic 插件目录（默认 $HERMES_HOME/plugins/limbic）")
    ap.add_argument("--cache-root", default=os.path.expanduser("~/.cache/limbic"),
                    help="模型缓存根目录（默认 ~/.cache/limbic，插件写在 HERMES_HOME 之外）")
    ap.add_argument("--source", default="https://huggingface.co",
                    help="模型来源（默认 huggingface.co；国内可换镜像，注意镜像可能给旧内容）")
    ap.add_argument("--repair", action="store_true", help="补齐坏/缺的文件")
    ap.add_argument("--slices", type=int, default=6, help="大文件的并行分段数（默认 6）")
    args = ap.parse_args()

    pins = load_pins(args.plugin_dir)
    todo, bad = [], 0
    print("=== 校验（按 pin 的哈希规矩） ===", flush=True)
    for mid, (rev, files) in pins.items():
        dest_dir = os.path.join(args.cache_root, SUBDIR[mid])
        os.makedirs(dest_dir, exist_ok=True)
        for rel, expect in files.items():
            path = os.path.join(dest_dir, os.path.basename(rel))
            ok, got, size = check(path, expect)
            print(f"{'OK  ' if ok else 'BAD '} {SUBDIR[mid]}/{os.path.basename(rel):24s} "
                  f"{size:>13,} B  {got}", flush=True)
            if not ok:
                bad += 1
                todo.append((mid, rev, rel, expect, path, size))
    if not bad:
        print("=== 全部对上 ===")
        return 0
    print(f"=== {bad} 个文件需要修复 ===", flush=True)
    if not args.repair:
        print("（加 --repair 才会补）")
        return 1

    for mid, rev, rel, expect, path, size in todo:
        url = f"{args.source}/{mid}/resolve/{rev}/{rel}"
        total = remote_size(url)
        started = time.time()
        print(f"-> {rel}  远端 {total:,} B / 本地 {size:,} B", flush=True)
        if total > PARALLEL_MIN and size < total * 0.9:
            if os.path.exists(path):
                os.remove(path)                      # 残文件不与新内容拼接，整份重取
            print(f"   {args.slices} 路并行分段", flush=True)
            fetch_slices(url, path, total, args.slices)
        else:
            fetch_single(url, path)
        ok, got, _ = check(path, expect)
        print(f"   {'OK' if ok else '仍然不对'}  {time.time() - started:.0f}s  {got}", flush=True)
        if not ok:
            print("补齐后哈希仍不匹配 —— 换 --source（镜像可能给旧内容）后重试", file=sys.stderr)
            return 1
    print("=== 修复后全部对上 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
