import { useEffect, useState } from "react";
import type { Filters, RecipeDetail, RecipeEnhanceResponse } from "../types";
import { enhanceRecipe } from "../api";
import { bucketClass, bucketIcon } from "../bucket";

interface Props {
  open: boolean;
  loading: boolean;
  error: string | null;
  detail: RecipeDetail | null;
  bucket?: string;
  context: { items: string[]; excluded: string[]; filters: Filters };
  onClose: () => void;
}

export default function RecipeDetailModal({
  open,
  loading,
  error,
  detail,
  bucket,
  context,
  onClose,
}: Props) {
  const [enhanceLoading, setEnhanceLoading] = useState(false);
  const [enhanceError, setEnhanceError] = useState<string | null>(null);
  const [enhanced, setEnhanced] = useState<RecipeEnhanceResponse | null>(null);

  // 切换菜谱时清空上一条的 AI 结果。
  useEffect(() => {
    setEnhanced(null);
    setEnhanceError(null);
    setEnhanceLoading(false);
  }, [detail?.recipe_id]);

  if (!open) return null;

  const required = detail?.ingredients.filter((i) => i.required) ?? [];
  const seasonings = detail?.ingredients.filter((i) => !i.required) ?? [];

  const runEnhance = async () => {
    if (!detail) return;
    setEnhanceLoading(true);
    setEnhanceError(null);
    try {
      const res = await enhanceRecipe(detail.recipe_id, {
        user_items: context.items,
        excluded_items: context.excluded,
        preferences: context.filters,
      });
      setEnhanced(res);
    } catch (e) {
      setEnhanceError(e instanceof Error ? e.message : "AI 生成失败");
    } finally {
      setEnhanceLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="关闭">
          ×
        </button>

        {loading && <div className="modal-state">加载中…</div>}
        {error && <div className="modal-state error">{error}</div>}

        {detail && !loading && !error && (
          <>
            <div className="modal-head">
              <div>
                <h2 className="modal-title">{detail.title}</h2>
                {detail.dish && <div className="modal-dish">{detail.dish}</div>}
              </div>
              {bucket && (
                <span className={bucketClass(bucket)}>
                  {bucketIcon(bucket)} {bucket}
                </span>
              )}
            </div>

            {detail.recipe_tags.length > 0 && (
              <div className="chip-row">
                {detail.recipe_tags.map((t) => (
                  <span key={t} className="chip chip-tag">{t}</span>
                ))}
              </div>
            )}

            {detail.description && <p className="modal-desc">{detail.description}</p>}

            <h4 className="modal-h">必需食材</h4>
            <ul className="ing-list">
              {required.length === 0 && <li className="muted">无</li>}
              {required.map((i) => (
                <li key={i.position}>
                  {i.raw_text}
                  {i.canonical_name && <span className="ing-canon">{i.canonical_name}</span>}
                </li>
              ))}
            </ul>

            {seasonings.length > 0 && (
              <>
                <h4 className="modal-h">基础调味品</h4>
                <ul className="ing-list">
                  {seasonings.map((i) => (
                    <li key={i.position}>{i.raw_text}</li>
                  ))}
                </ul>
              </>
            )}

            <h4 className="modal-h">步骤</h4>
            <ol className="step-list">
              {detail.steps.map((s) => (
                <li key={s.step_no}>{s.text}</li>
              ))}
            </ol>

            {/* AI 改良做法 */}
            <div className="enhance">
              <div className="enhance-bar">
                <span className="enhance-title">🤖 AI 改良做法</span>
                <button className="enhance-btn" onClick={runEnhance} disabled={enhanceLoading}>
                  {enhanceLoading ? "生成中…" : enhanced ? "重新生成" : "按我的食材和偏好生成"}
                </button>
              </div>

              {enhanceError && <div className="enhance-error">{enhanceError}</div>}

              {enhanced && (
                <div className="enhance-result">
                  <div className="enhance-head">
                    <h3 className="enhance-gen-title">{enhanced.generated_title}</h3>
                    <span className={bucketClass(enhanced.bucket)}>
                      {bucketIcon(enhanced.bucket)} {enhanced.bucket}
                    </span>
                  </div>
                  <p className="enhance-summary">{enhanced.summary}</p>
                  <p className="enhance-bucket-reason">{enhanced.bucket_reason}</p>

                  {(enhanced.matched.length > 0 || enhanced.missing.length > 0) && (
                    <div className="chip-row">
                      {enhanced.matched.map((t) => (
                        <span key={"m" + t} className="chip chip-matched">{t}</span>
                      ))}
                      {enhanced.missing.map((t) => (
                        <span key={"x" + t} className="chip chip-missing">{t}</span>
                      ))}
                    </div>
                  )}

                  <h4 className="modal-h">食材</h4>
                  <ul className="ing-list">
                    {enhanced.ingredients.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>

                  <h4 className="modal-h">步骤</h4>
                  <ol className="step-list">
                    {enhanced.steps.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ol>

                  {enhanced.tips.length > 0 && (
                    <>
                      <h4 className="modal-h">小贴士</h4>
                      <ul className="ing-list">
                        {enhanced.tips.map((t, i) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </>
                  )}

                  <p className="enhance-disclaimer">
                    {enhanced.disclaimer}（模型：{enhanced.model}）
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
