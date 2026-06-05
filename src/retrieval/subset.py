"""从 recipes.jsonl 抽一个"种类丰富"的小子集（默认 2500 条）。

多样性策略：以每条菜谱的"主食材"分桶，轮转(round-robin)地从各桶各取一条，
使子集尽量覆盖更多不同的主食材，而不是堆满同一类菜。
同时做质量过滤：去掉食材名没切干净的脏记录、步骤太少的记录、重复食材组合。

两遍扫描：第一遍只读元数据选行号（省内存），第二遍按行号原样取出整条记录。

用法（在项目根目录运行）：
    python3 -m src.retrieval.subset                 # 默认 2500 条
    python3 -m src.retrieval.subset --target 3000
"""
import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from .config import normalize_ingredient, PANTRY_STAPLES

_BAD_CHARS = set("：:，,。、；;()（）【】[]{}=+*#/\\")
_BAD_WORDS = ("主料", "配料", "辅料", "食材", "调料", "做法", "克", "毫升", "适量", "少许")


def is_clean_name(n: str) -> bool:
    """食材名是否"干净"（排除没切开的整块食材文本）。"""
    if not (2 <= len(n) <= 8):
        return False
    if any(c in _BAD_CHARS for c in n):
        return False
    if any(w in n for w in _BAD_WORDS):
        return False
    if re.search(r"\d", n):
        return False
    return True


def primary_ingredient(names):
    """取主食材：第一个干净且非调料的食材；没有则返回 None。"""
    clean = [n for n in names if is_clean_name(n)]
    if len(clean) < 3 or len(clean) / max(1, len(names)) < 0.6:
        return None
    for n in clean:
        if normalize_ingredient(n) not in PANTRY_STAPLES:
            return n
    return clean[0]


def select_rows(in_path: Path, target: int, cap_per_primary: int, seed: int):
    """第一遍：分桶 + 去重，挑出要保留的行号集合。"""
    buckets = defaultdict(list)
    seen_sig = set()
    for i, line in enumerate(_iter_lines(in_path)):
        r = json.loads(line)
        names = r.get("ingredient_names", [])
        if r.get("n_steps", 0) < 2:
            continue
        prim = primary_ingredient(names)
        if prim is None:
            continue
        sig = hash(frozenset(normalize_ingredient(n) for n in names))
        if sig in seen_sig:
            continue
        b = buckets[normalize_ingredient(prim)]
        if len(b) >= cap_per_primary:
            continue
        seen_sig.add(sig)
        b.append(i)

    # 轮转抽样：打乱桶顺序与桶内顺序，逐轮各取一条
    rng = random.Random(seed)
    keys = list(buckets.keys())
    rng.shuffle(keys)
    for k in keys:
        rng.shuffle(buckets[k])

    chosen = []
    round_i = 0
    while len(chosen) < target:
        progressed = False
        for k in keys:
            if round_i < len(buckets[k]):
                chosen.append(buckets[k][round_i])
                progressed = True
                if len(chosen) >= target:
                    break
        if not progressed:
            break
        round_i += 1
    return set(chosen), len(buckets)


def write_subset(in_path: Path, chosen: set, out_path: Path):
    """第二遍：按选中的行号原样写出整条记录。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    primaries = set()
    n = 0
    with out_path.open("w", encoding="utf-8") as out_f:
        for i, line in enumerate(_iter_lines(in_path)):
            if i in chosen:
                out_f.write(line if line.endswith("\n") else line + "\n")
                r = json.loads(line)
                p = primary_ingredient(r.get("ingredient_names", []))
                if p:
                    primaries.add(normalize_ingredient(p))
                n += 1
    return n, len(primaries)


def _iter_lines(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


def main():
    ap = argparse.ArgumentParser(description="抽取种类丰富的菜谱子集")
    ap.add_argument("--input", default="data/processed/recipes.jsonl")
    ap.add_argument("--out", default="data/processed/recipes_subset.jsonl")
    ap.add_argument("--target", type=int, default=2500)
    ap.add_argument("--cap-per-primary", type=int, default=3,
                    help="同一主食材最多保留几条")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"找不到输入：{in_path}")

    chosen, n_buckets = select_rows(in_path, args.target, args.cap_per_primary, args.seed)
    n, n_prim = write_subset(in_path, chosen, Path(args.out))

    print("\n===== 子集生成报告 =====")
    print(f"  候选主食材桶数 : {n_buckets}")
    print(f"  目标条数       : {args.target}")
    print(f"  实际写出       : {n}")
    print(f"  覆盖主食材种类 : {n_prim}")
    print("========================")
    print(f"已写出：{args.out}")


if __name__ == "__main__":
    main()
