import { useEffect, useState } from "react";
import type { Filters, RecipeDetail, SearchItem, SearchResponse } from "./types";
import { searchByIngredients, getRecipe, checkHealth } from "./api";
import TagInput from "./components/TagInput";
import FiltersPanel from "./components/Filters";
import ResultCard from "./components/ResultCard";
import RecipeDetailModal from "./components/RecipeDetailModal";

const PAGE_SIZE = 12;

export default function App() {
  const [items, setItems] = useState<string[]>(["西红柿", "鸡蛋"]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filters>({ count_seasonings_as_ingredients: false });
  const [page, setPage] = useState(1);

  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<RecipeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SearchItem | null>(null);

  useEffect(() => {
    checkHealth().then(setBackendOk);
  }, []);

  const doSearch = async (toPage = 1) => {
    setLoading(true);
    setError(null);
    setSearched(true);
    setPage(toPage);
    try {
      const data = await searchByIngredients({
        items,
        excluded_items: excluded,
        filters,
        page: toPage,
        page_size: PAGE_SIZE,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "搜索失败");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const openDetail = async (item: SearchItem) => {
    setSelected(item);
    setDetailOpen(true);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setDetail(await getRecipe(item.recipe_id));
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const totalPages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          FridgeIR <span>冰箱里有啥</span>
        </div>
        <div className="backend-status">
          {backendOk === null ? (
            "检测后端…"
          ) : backendOk ? (
            <span className="ok">● 后端已连接</span>
          ) : (
            <span className="down">● 后端未连接</span>
          )}
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <TagInput
            label="已有食材"
            placeholder="输入食材，回车添加"
            tags={items}
            onChange={setItems}
            tone="have"
          />
          <TagInput
            label="不需要的食材"
            placeholder="不想吃的，回车添加"
            tags={excluded}
            onChange={setExcluded}
            tone="exclude"
          />
          <FiltersPanel value={filters} onChange={setFilters} />
          <button className="search-btn" onClick={() => doSearch(1)} disabled={loading}>
            {loading ? "搜索中…" : "搜索菜谱"}
          </button>
        </aside>

        <main className="main">
          {backendOk === false && (
            <div className="banner banner-warn">
              后端未连接。请先启动后端服务（默认 http://127.0.0.1:8000）再搜索。
            </div>
          )}

          {result?.parsed && (
            <div className="parsed">
              {result.parsed.ingredients.length > 0 && (
                <div className="parsed-row">
                  <span className="parsed-label">识别到</span>
                  {result.parsed.ingredients.map((p) => (
                    <span key={p.raw} className="chip chip-parsed" title={`原始：${p.raw}`}>
                      {p.canonical}
                    </span>
                  ))}
                </div>
              )}
              {result.parsed.excluded_ingredients.length > 0 && (
                <div className="parsed-row">
                  <span className="parsed-label">不需要</span>
                  {result.parsed.excluded_ingredients.map((t) => (
                    <span key={t} className="chip chip-missing">{t}</span>
                  ))}
                </div>
              )}
              {result.parsed.need_confirmation.length > 0 && (
                <div className="parsed-row">
                  <span className="parsed-label">待确认</span>
                  {result.parsed.need_confirmation.map((t) => (
                    <span key={t} className="chip chip-warn">{t}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          {error && <div className="banner banner-error">{error}</div>}

          {result && !error && (
            <div className="result-meta">
              <span>
                共 <b>{result.total}</b> 个结果
              </span>
              {result.facets?.bucket?.map((f) => (
                <span key={f.name} className="facet">
                  {f.name} {f.count}
                </span>
              ))}
            </div>
          )}

          {loading && <div className="state">搜索中…</div>}
          {!loading && !searched && (
            <div className="state">输入你有的食材，点击「搜索菜谱」开始。</div>
          )}
          {!loading && searched && result && result.items.length === 0 && !error && (
            <div className="state">没有匹配的菜谱，试着减少偏好或更换食材。</div>
          )}

          <div className="cards">
            {result?.items.map((it) => (
              <ResultCard key={it.recipe_id} item={it} onClick={() => openDetail(it)} />
            ))}
          </div>

          {result && result.total > PAGE_SIZE && (
            <div className="pager">
              <button disabled={page <= 1 || loading} onClick={() => doSearch(page - 1)}>
                上一页
              </button>
              <span>
                第 {page} / {totalPages} 页
              </span>
              <button disabled={page >= totalPages || loading} onClick={() => doSearch(page + 1)}>
                下一页
              </button>
            </div>
          )}
        </main>
      </div>

      <RecipeDetailModal
        open={detailOpen}
        loading={detailLoading}
        error={detailError}
        detail={detail}
        bucket={selected?.bucket}
        context={{ items, excluded, filters }}
        onClose={() => setDetailOpen(false)}
      />
    </div>
  );
}
