import { useState, type KeyboardEvent } from "react";

interface Props {
  label: string;
  placeholder?: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  tone?: "have" | "exclude";
}

export default function TagInput({ label, placeholder, tags, onChange, tone = "have" }: Props) {
  const [text, setText] = useState("");

  const add = (raw: string) => {
    const parts = raw.split(/[，,、\s]+/).map((s) => s.trim()).filter(Boolean);
    if (!parts.length) return;
    const next = [...tags];
    for (const p of parts) if (!next.includes(p)) next.push(p);
    onChange(next);
    setText("");
  };
  const remove = (t: string) => onChange(tags.filter((x) => x !== t));

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add(text);
    } else if (e.key === "Backspace" && !text && tags.length) {
      remove(tags[tags.length - 1]);
    }
  };

  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className={`tag-input tag-${tone}`}>
        {tags.map((t) => (
          <span key={t} className="chip chip-removable" onClick={() => remove(t)}>
            {t}
            <span className="chip-x">×</span>
          </span>
        ))}
        <input
          className="tag-input-field"
          value={text}
          placeholder={tags.length ? "" : placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          onBlur={() => add(text)}
        />
      </div>
    </div>
  );
}
