import { useRef, useState } from "react";
import { Upload, CheckCircle2 } from "lucide-react";

export default function DropZone({ accept = ".pdf", label = "Glisser-déposer ou cliquer", onChange }) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const ref = useRef(null);

  function pick(f) {
    setFile(f);
    onChange?.(f);
  }

  const base = "rounded-lg p-5 text-center cursor-pointer transition-colors border-[1.5px] border-dashed";
  const idle = "border-black/20 hover:border-primary hover:bg-primary-light/40";
  const drag = "border-primary bg-primary-light";
  const done = "border-green-400 bg-green-50";

  return (
    <div
      className={`${base} ${file ? done : dragging ? drag : idle}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pick(f); }}
      onClick={() => ref.current?.click()}
    >
      <input ref={ref} type="file" accept={accept} hidden onChange={(e) => { const f = e.target.files[0]; if (f) pick(f); }} />
      {file ? (
        <div className="flex items-center justify-center gap-2">
          <CheckCircle2 size={15} className="text-green-500 shrink-0" />
          <span className="text-[13px] text-gray-700 truncate max-w-[180px]">{file.name}</span>
          <span className="text-[11px] text-muted shrink-0">({(file.size / 1024).toFixed(0)} Ko)</span>
        </div>
      ) : (
        <>
          <Upload size={20} className="mx-auto mb-2 text-muted" />
          <p className="text-[12px] text-muted">{label}</p>
        </>
      )}
    </div>
  );
}
