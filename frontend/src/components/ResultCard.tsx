import type { SearchItem } from "../types";
import { bucketClass, bucketIcon } from "../bucket";

interface Props {
  item: SearchItem;
  onClick: () => void;
}

export default function ResultCard({ item, onClick }: Props) {
  return (
    <div className="card" onClick={onClick}>
      <div className="card-head">
        <div className="card-titles">
          <h3 className="card-title">{item.title}</h3>
          {item.dish && <div className="card-dish">{item.dish}</div>}
        </div>
        <span className={bucketClass(item.bucket)}>
          {bucketIcon(item.bucket)} {item.bucket}
        </span>
      </div>

      {item.matched.length > 0 && (
        <div className="chip-row">
          <span className="chip-row-label">已匹配</span>
          {item.matched.map((t) => (
            <span key={t} className="chip chip-matched">{t}</span>
          ))}
        </div>
      )}

      {item.missing.length > 0 && (
        <div className="chip-row">
          <span className="chip-row-label">还缺</span>
          {item.missing.map((t) => (
            <span key={t} className="chip chip-missing">{t}</span>
          ))}
        </div>
      )}

      {item.recipe_tags.length > 0 && (
        <div className="chip-row">
          {item.recipe_tags.map((t) => (
            <span
              key={t}
              className={`chip ${item.preference_matches.includes(t) ? "chip-pref" : "chip-tag"}`}
            >
              {t}
            </span>
          ))}
        </div>
      )}

      <p className="card-reason">{item.reason}</p>
      {item.rerank_reason && <p className="card-rerank">🤖 重排：{item.rerank_reason}</p>}

      <div className="card-foot">点击查看详情 / AI 改良做法 →</div>
    </div>
  );
}
