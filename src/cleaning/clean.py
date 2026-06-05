"""FoodieIR 数据提取流水线（XiaChuFang recipe_corpus_full.json）。

从原始语料逐行流式提取检索所需字段，不合成原始数据里不存在的字段：
  name / dish / description / 结构化食材(原文+食材名) / 步骤

用法（在项目根目录运行）：
    python3 -m src.cleaning.clean                              # 默认处理 data/raw 全量
    python3 -m src.cleaning.clean --input data/raw/x.jsonl     # 处理指定文件
    python3 -m src.cleaning.clean --limit 5000                 # 只处理前 5000 条
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from .config import FIELD_MAP, MIN_INGREDIENTS, MIN_STEPS
from .ingredient_parser import normalize_text, extract_ingredient_names


def iter_records(path: Path):
    """逐行读取（语料是 JSONL，即使后缀是 .json）；坏行跳过。"""
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def remap_fields(rec: dict) -> dict:
    return {std: rec[src] for src, std in FIELD_MAP.items() if src in rec}


def clean_steps(raw_steps) -> list:
    """步骤标准化：拆分、去序号前缀、去 HTML、合并空白、去空步骤。"""
    if raw_steps is None:
        return []
    if isinstance(raw_steps, str):
        parts = re.split(r"[\n。；]+", raw_steps)
    elif isinstance(raw_steps, (list, tuple)):
        parts = list(raw_steps)
    else:
        parts = [raw_steps]

    out = []
    for s in parts:
        s = normalize_text(s)
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"^\s*\d+\s*[\.、,，:：)）]\s*", "", s)
        if s:
            out.append(s)
    return out


def _dedup_keep_order(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_record(rec: dict):
    """把一条原始记录提成标准记录；无效返回 (None, 原因)。"""
    rec = remap_fields(rec)

    name = normalize_text(rec.get("name", ""))
    if not name:
        return None, "empty_name"

    pairs = extract_ingredient_names(rec.get("ingredients"))
    ingredient_names = _dedup_keep_order([n for _, n in pairs])
    if len(ingredient_names) < MIN_INGREDIENTS:
        return None, "few_ingredients"

    steps = clean_steps(rec.get("steps"))
    if len(steps) < MIN_STEPS:
        return None, "few_steps"

    dish = normalize_text(rec.get("dish", ""))
    if dish.lower() == "unknown":
        dish = ""

    out = {
        "name": name,
        "dish": dish,
        "description": normalize_text(rec.get("description", "")),
        "ingredients": [{"raw": r, "name": n} for r, n in pairs],
        "ingredient_names": ingredient_names,
        "n_ingredients": len(ingredient_names),
        "steps": steps,
        "n_steps": len(steps),
    }
    return out, None


def run(in_path: Path, out_dir: Path, limit=None, preview_n=300):
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "recipes.jsonl"

    stats = {"total_raw": 0, "kept": 0,
             "empty_name": 0, "few_ingredients": 0, "few_steps": 0, "duplicate": 0}
    seen = set()              # 去重：name+食材集合 的 hash
    n_ing_sum = 0
    preview = []

    with jsonl_path.open("w", encoding="utf-8") as out_f:
        for i, rec in enumerate(iter_records(in_path)):
            if limit is not None and i >= limit:
                break
            stats["total_raw"] += 1

            row, reason = extract_record(rec)
            if row is None:
                stats[reason] += 1
                continue

            sig = hash((row["name"], tuple(sorted(row["ingredient_names"]))))
            if sig in seen:
                stats["duplicate"] += 1
                continue
            seen.add(sig)

            out_id = f"r{stats['kept']+1:07d}"
            row = {"id": out_id, **row}
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")

            stats["kept"] += 1
            n_ing_sum += row["n_ingredients"]
            if len(preview) < preview_n:
                preview.append(row)

            if stats["total_raw"] % 200000 == 0:
                print(f"  ...已处理 {stats['total_raw']} 条，保留 {stats['kept']}")

    stats["avg_ingredients"] = round(n_ing_sum / stats["kept"], 2) if stats["kept"] else 0

    # 预览 CSV（前 preview_n 条，方便人工核对）
    csv_path = out_dir / "recipes_preview.csv"
    pd.DataFrame([{
        "id": r["id"], "name": r["name"], "dish": r["dish"],
        "ingredient_names": " | ".join(r["ingredient_names"]),
        "n_ingredients": r["n_ingredients"], "n_steps": r["n_steps"],
        "steps": " || ".join(r["steps"]),
    } for r in preview]).to_csv(csv_path, index=False, encoding="utf-8-sig")

    report_path = out_dir / "quality_report.json"
    report_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 数据提取报告 =====")
    for k in ["total_raw", "kept", "empty_name", "few_ingredients", "few_steps",
              "duplicate", "avg_ingredients"]:
        print(f"  {k:16s}: {stats[k]}")
    print("========================")
    print(f"已写出：\n  {jsonl_path}\n  {csv_path}\n  {report_path}")


def main():
    ap = argparse.ArgumentParser(description="FoodieIR 菜谱数据提取")
    ap.add_argument("--input", default="data/raw/recipe_corpus_full.json")
    ap.add_argument("--outdir", default="data/processed")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条（调试用）")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"找不到输入文件：{in_path}")
    run(in_path, Path(args.outdir), limit=args.limit)


if __name__ == "__main__":
    main()
