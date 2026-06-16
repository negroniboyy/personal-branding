import { useEffect, useState } from "react";
import { API_BASE as BASE } from "../apiBase";

export function ModelSelector({ task, value, onChange }) {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    fetch(`${BASE}/openrouter/models`)
      .then((r) => r.json())
      .then((data) => {
        if (data[task]) setOptions(data[task].chain);
      })
      .catch(() => {});
  }, [task]);

  if (options.length === 0) return null;

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      title="Model"
      className="glass-panel rounded-lg px-3 py-2 font-label-caps text-label-caps text-on-surface appearance-none focus:border-primary outline-none border-black/5 cursor-pointer max-w-[200px] truncate"
    >
      {options.map((m) => (
        <option key={m} value={m} className="text-on-surface">
          {m}
        </option>
      ))}
    </select>
  );
}
