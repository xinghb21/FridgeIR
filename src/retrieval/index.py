"""构建食材倒排索引。

读 data/processed/recipes.jsonl，对每条菜谱的食材名做归一，建立：
  - id2ing        : 食材词表（下标即食材 token id）
  - postings      : 食材id -> 含该食材的菜谱行号列表（倒排表）
  - recipe_ings   : 菜谱行号 -> 该菜谱的食材id元组
  - recipe_ids/names : 菜谱行号 -> 原始id / 菜名
整体 pickle 到 data/index/index.pkl，供 search.py 加载。

用法（在项目根目录运行）：
    python3 -m src.retrieval.index                 # 全量
    python3 -m src.retrieval.index --limit 200000  # 只建前 N 条（更快/更省内存）
"""
import argparse
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

from .config import normalize_ingredient


def build(in_path: Path, out_path: Path, limit=None):
    id2ing = []
    ing2id = {}

    def get_id(tok):
        i = ing2id.get(tok)
        if i is None:
            i = len(id2ing)
            ing2id[tok] = i
            id2ing.append(tok)
        return i

    recipe_ids, recipe_names, recipe_ings = [], [], []
    postings = defaultdict(list)

    t0 = time.time()
    row = 0
    with in_path.open(encoding="utf-8") as f:
        for n, line in enumerate(f):
            if limit is not None and n >= limit:
                break
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)

            seen, ids = set(), []
            for nm in r.get("ingredient_names", []):
                tok = normalize_ingredient(nm)
                if not tok:
                    continue
                tid = get_id(tok)
                if tid in seen:
                    continue
                seen.add(tid)
                ids.append(tid)
            if not ids:
                continue

            recipe_ids.append(r["id"])
            recipe_names.append(r["name"])
            recipe_ings.append(tuple(ids))
            for tid in ids:
                postings[tid].append(row)
            row += 1

            if row % 200000 == 0:
                print(f"  ...已索引 {row} 条，词表 {len(id2ing)}")

    index = {
        "id2ing": id2ing,
        "postings": dict(postings),
        "recipe_ings": recipe_ings,
        "recipe_ids": recipe_ids,
        "recipe_names": recipe_names,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"\n索引完成：{row} 条菜谱，{len(id2ing)} 个食材，"
          f"{sum(len(v) for v in postings.values())} 条倒排，耗时 {time.time()-t0:.1f}s")
    print(f"已写出：{out_path}（{out_path.stat().st_size/1e6:.1f} MB）")


def main():
    ap = argparse.ArgumentParser(description="构建食材倒排索引")
    ap.add_argument("--input", default="data/processed/recipes.jsonl")
    ap.add_argument("--out", default="data/index/index.pkl")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"找不到输入：{in_path}（先跑 clean.py）")
    build(in_path, Path(args.out), limit=args.limit)


if __name__ == "__main__":
    main()
