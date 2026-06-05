import type {
  Filters as F,
  CookMethod,
  Spice,
  Diet,
  Complexity,
  ServingSize,
  SeasoningAmount,
} from "../types";
import SegmentedControl from "./SegmentedControl";

const METHODS: CookMethod[] = ["炒", "蒸", "煎", "拌", "炖", "炸"];

interface Props {
  value: F;
  onChange: (f: F) => void;
}

export default function Filters({ value, onChange }: Props) {
  const set = (patch: Partial<F>) => onChange({ ...value, ...patch });

  const toggleMethod = (m: CookMethod) => {
    const cur = value.methods ?? [];
    set({ methods: cur.includes(m) ? cur.filter((x) => x !== m) : [...cur, m] });
  };

  return (
    <div className="filters">
      <div className="filters-title">偏好</div>

      <SegmentedControl<Spice | null>
        label="辣度"
        value={value.spice ?? null}
        onChange={(v) => set({ spice: v })}
        options={[
          { label: "不限", value: null },
          { label: "辣", value: "spicy" },
          { label: "不辣", value: "not_spicy" },
        ]}
      />
      <SegmentedControl<Diet | null>
        label="荤素"
        value={value.diet ?? null}
        onChange={(v) => set({ diet: v })}
        options={[
          { label: "不限", value: null },
          { label: "荤菜", value: "meat" },
          { label: "素菜", value: "vegetarian" },
        ]}
      />
      <SegmentedControl<Complexity | null>
        label="难度"
        value={value.complexity ?? null}
        onChange={(v) => set({ complexity: v })}
        options={[
          { label: "不限", value: null },
          { label: "简单", value: "simple" },
          { label: "复杂", value: "complex" },
        ]}
      />
      <SegmentedControl<ServingSize | null>
        label="分量"
        value={value.serving_size ?? null}
        onChange={(v) => set({ serving_size: v })}
        options={[
          { label: "不限", value: null },
          { label: "多", value: "large" },
          { label: "少", value: "small" },
        ]}
      />
      <SegmentedControl<SeasoningAmount | null>
        label="调料"
        value={value.seasoning_amount ?? null}
        onChange={(v) => set({ seasoning_amount: v })}
        options={[
          { label: "不限", value: null },
          { label: "多", value: "many" },
          { label: "少", value: "few" },
        ]}
      />

      <div className="seg">
        <span className="seg-label">烹饪手法</span>
        <div className="seg-buttons wrap">
          {METHODS.map((m) => (
            <button
              key={m}
              type="button"
              className={`seg-btn ${(value.methods ?? []).includes(m) ? "active" : ""}`}
              onClick={() => toggleMethod(m)}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="toggles">
        <label className="toggle">
          <input
            type="checkbox"
            checked={!!value.for_children}
            onChange={(e) => set({ for_children: e.target.checked })}
          />
          适合小孩
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={!!value.count_seasonings_as_ingredients}
            onChange={(e) => set({ count_seasonings_as_ingredients: e.target.checked })}
          />
          调味料算食材
        </label>
      </div>
    </div>
  );
}
