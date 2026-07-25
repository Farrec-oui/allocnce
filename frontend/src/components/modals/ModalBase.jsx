import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

export default function ModalBase({ open, onClose, title, subtitle, children }) {
  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div
        className="dialog-overlay absolute inset-0 bg-black/30"
        onClick={onClose}
      />
      <div className="dialog-content relative bg-white rounded-xl border border-black/15 shadow-xl w-[400px] max-w-[calc(100vw-32px)] max-h-[90vh] overflow-y-auto z-10">
        <div className="px-6 pt-5 pb-4">
          <div className="flex items-start justify-between mb-1">
            <span className="text-[15px] font-semibold text-text">{title}</span>
            <button
              onClick={onClose}
              className="text-muted hover:text-text p-1 rounded-md transition-colors -mr-1"
            >
              <X size={15} />
            </button>
          </div>
          {subtitle && <p className="text-[12px] text-muted mb-3">{subtitle}</p>}
        </div>
        <div className="border-t border-black/8" />
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>,
    document.body
  );
}
