#!/usr/bin/env python3
"""看 .pse 里到底有什么: 对象清单 + 每个对象的原子数 / Fe 数; 给两个文件时逐对象比对。

为什么不是 `cmp`: .pse **不逐字节稳定** —— 同一套脚本连跑两次字节数相同而字节不同。
核对 .pse 要比结构 (对象名集合 + 原子数), 别比字节。

用法 (PyMOL 自带的解释器; biorazer_pymol 会屏蔽 CLI 二进制)::

    "$PYMOL_ROOT/Contents/bin/python3.10" inspect_pse.py a.pse [b.pse]

比对判据: 对象名集合相同 + 每个对象的原子数 (原子数, Fe 数) 相同; 不同就打印哪几项不同, 退出码 1
—— 可以直接当验收命令用。
"""
import sys

from pymol import cmd, finish_launching


def inspect(path):
    """加载一个 .pse -> {对象名: (原子数, Fe 原子数)}。"""
    cmd.reinitialize()
    cmd.load(path)
    return {o: (cmd.count_atoms(o), cmd.count_atoms(f"{o} and elem FE"))
            for o in cmd.get_names("objects")}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    finish_launching(["pymol", "-qc"])
    ref = inspect(sys.argv[1])
    print(f"{sys.argv[1]}: {len(ref)} 个对象")
    for obj, (n_atom, n_fe) in ref.items():
        line = f"    {obj:12s} 原子 {n_atom:7d}"
        if n_fe:
            line += f"  Fe {n_fe}"
        print(line)
    if len(sys.argv) < 3:
        return 0

    other = inspect(sys.argv[2])
    print(f"{sys.argv[2]}: {len(other)} 个对象")
    bad = []
    if set(ref) != set(other):
        bad.append(f"对象名集合不同: 只在前者 {sorted(set(ref) - set(other))}; "
                   f"只在后者 {sorted(set(other) - set(ref))}")
    for obj in sorted(set(ref) & set(other)):
        if ref[obj] != other[obj]:
            bad.append(f"{obj}: 原子数 {ref[obj]} vs {other[obj]}")
    if bad:
        print("\n".join(bad))
        return 1
    print("两个 .pse 的对象结构与原子数一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
