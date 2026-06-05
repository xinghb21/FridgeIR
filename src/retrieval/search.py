"""基于食材的弹性检索：输入手头食材，返回能做/差一两样就能做的菜谱。

弹性体现在三点：
  1) 近似召回：查询词按"精确 + 子串"扩展（"娃娃菜"能命中"高山娃娃菜"）；
  2) 调料默认有：常备调料不计入"还差的食材"；
  3) 容缺匹配：--max-missing 允许菜谱还差 N 样非调料食材也返回。

排序：命中查询食材数 多者优先 -> 还差的食材 少者优先 -> 食材总数 少者优先。

用法（在项目根目录运行）：
    python3 -m src.retrieval.search 西红柿 鸡蛋
    python3 -m src.retrieval.search 五花肉 土豆 --max-missing 1 --topk 10
"""
import argparse
import pickle
import sys
from pathlib import Path

from .config import normalize_ingredient, PANTRY_STAPLES


def load_index(path: Path):
    with path.open("rb") as f:
        idx = pickle.load(f)
    idx["ing2id"] = {t: i for i, t in enumerate(idx["id2ing"])}
    idx["staple_ids"] = {idx["ing2id"][s] for s in PANTRY_STAPLES if s in idx["ing2id"]}
    return idx


def expand_term(term: str, idx) -> set:
    """把一个查询食材扩展成索引里的 token id 集合（精确 + 子串）。"""
    term = normalize_ingredient(term)
    hits = set()
    tid = idx["ing2id"].get(term)
    if tid is not None:
        hits.add(tid)
    if len(term) >= 2:                       # 单字不做子串，避免噪声
        for i, tok in enumerate(idx["id2ing"]):
            if term in tok:
                hits.add(i)
    return hits


def search(query_terms, idx, max_missing=2, topk=10):
    term_tokens = [expand_term(t, idx) for t in query_terms]
    query_tokens = set().union(*term_tokens) if term_tokens else set()

    # 候选：含任一查询食材的菜谱
    cand = set()
    for tid in query_tokens:
        cand.update(idx["postings"].get(tid, ()))

    staples = idx["staple_ids"]
    results = []
    for row in cand:
        ings = set(idx["recipe_ings"][row])
        covered = sum(1 for ts in term_tokens if ings & ts)   # 命中的查询食材数
        if covered == 0:
            continue
        core = ings - staples                                 # 非调料食材
        missing = core - query_tokens                         # 用户还差的食材
        if len(missing) > max_missing:
            continue
        score = (covered, -len(missing), -len(core))
        results.append((score, row, ings & query_tokens, missing))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:topk]


def fmt_ings(ids, idx):
    return [idx["id2ing"][i] for i in ids]


def main():
    ap = argparse.ArgumentParser(description="食材弹性检索")
    ap.add_argument("ingredients", nargs="+", help="手头的食材，空格分隔")
    ap.add_argument("--index", default="data/index/index.pkl")
    ap.add_argument("--max-missing", type=int, default=2, help="允许菜谱还差几样非调料食材")
    ap.add_argument("--topk", type=int, default=10)
    args = ap.parse_args()

    idx_path = Path(args.index)
    if not idx_path.exists():
        sys.exit(f"找不到索引：{idx_path}（先跑 build_index.py）")

    idx = load_index(idx_path)
    hits = search(args.ingredients, idx, args.max_missing, args.topk)

    print(f"\n手头食材：{' / '.join(args.ingredients)}    "
          f"(允许还差 ≤ {args.max_missing} 样)")
    if not hits:
        print("没有匹配的菜谱，试着放宽 --max-missing。")
        return
    print(f"共 {len(hits)} 条结果：\n")
    for rank, (score, row, matched, missing) in enumerate(hits, 1):
        covered, neg_missing, _ = score
        line = f"{rank}. {idx['recipe_names'][row]}  [{idx['recipe_ids'][row]}]"
        print(line)
        print(f"     用上：{' '.join(fmt_ings(matched, idx)) or '-'}")
        if missing:
            print(f"     还差：{' '.join(fmt_ings(missing, idx))}")
        else:
            print(f"     还差：无，食材齐全 ✅")
        print()


if __name__ == "__main__":
    main()
