interface Option<T> {
  label: string;
  value: T;
}

interface Props<T> {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (v: T) => void;
}

export default function SegmentedControl<T extends string | boolean | null>(
  props: Props<T>
) {
  const { label, value, options, onChange } = props;
  return (
    <div className="seg">
      <span className="seg-label">{label}</span>
      <div className="seg-buttons">
        {options.map((o, i) => (
          <button
            key={i}
            type="button"
            className={`seg-btn ${o.value === value ? "active" : ""}`}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
