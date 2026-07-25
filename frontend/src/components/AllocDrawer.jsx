import { createPortal } from "react-dom";
import { useCallback, useEffect, useState } from "react";
import { Download, Loader2, RefreshCw, X } from "lucide-react";
import { api } from "../api";

export default function AllocDrawer({ alloc, onClose, onDownload }) {
  const [html, setHtml] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(false);
    setHtml(null);
    try {
      setHtml(await api.previewAllocation(alloc.id));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [alloc.id]);

  useEffect(() => {
    loadPreview();
    document.body.style.overflow = "hidden";
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [loadPreview, onClose]);

  return createPortal(
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      <div className="drawer-panel relative bg-white shadow-2xl flex flex-col h-full" style={{ width: 520 }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-black/10 shrink-0">
          <span className="text-[14px] font-semibold text-text truncate mr-4">{alloc.label}</span>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onDownload(alloc)}
              className="flex items-center gap-1.5 text-[12px] text-primary hover:text-primary-hover font-medium transition-colors cursor-pointer"
            >
              <Download size={13} />
              Télécharger
            </button>
            <button
              onClick={onClose}
              className="text-muted hover:text-text transition-colors p-1 rounded-md"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto bg-white">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={22} className="animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-muted">
              <p className="text-[13px]">Impossible de charger l'aperçu</p>
              <button
                onClick={loadPreview}
                className="flex items-center gap-1.5 text-[12px] text-primary hover:text-primary-hover font-medium transition-colors"
              >
                <RefreshCw size={12} />
                Réessayer
              </button>
            </div>
          ) : (
            <div
              className="alloc-preview"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
