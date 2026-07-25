import { useRef, useState } from "react";

export default function FileDropZone({ label, accept = ".pdf", onChange, required = false }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const inputRef = useRef(null);

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    onChange(f);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      className={[
        "border-2 border-dashed rounded-lg p-5 cursor-pointer text-center select-none transition-colors outline-none",
        dragging
          ? "border-blue-400 bg-blue-50"
          : "border-gray-300 hover:border-blue-300 hover:bg-gray-50 focus:border-blue-400",
      ].join(" ")}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {file ? (
        <div className="text-sm">
          <span className="text-green-600 font-medium">📄 {file.name}</span>
          <span className="block text-xs text-gray-400 mt-0.5">
            {(file.size / 1024).toFixed(0)} Ko — Cliquer pour changer
          </span>
        </div>
      ) : (
        <div className="text-sm text-gray-500">
          <span className="block text-2xl mb-1">📂</span>
          <span className="font-medium">{label}</span>
          {!required && (
            <span className="block text-xs text-gray-400 mt-0.5">Optionnel</span>
          )}
          <span className="block text-xs text-gray-400 mt-0.5">Cliquer ou glisser-déposer</span>
        </div>
      )}
    </div>
  );
}
