import { createContext, useCallback, useContext, useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, XCircle, X } from "lucide-react";

const ToastContext = createContext(null);

function ToastItem({ toast, onDismiss }) {
  const isSuccess = toast.type === "success";
  return (
    <div
      className={[
        "toast-root flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg w-80",
        isSuccess
          ? "bg-[#EAF3DE] border-[#27500A]/20 text-[#27500A]"
          : "bg-[#FCEBEB] border-[#A32D2D]/20 text-[#A32D2D]",
      ].join(" ")}
    >
      {isSuccess ? (
        <CheckCircle2 size={16} className="shrink-0" />
      ) : (
        <XCircle size={16} className="shrink-0" />
      )}
      <span className="flex-1 text-[13px] font-medium">{toast.message}</span>
      <button onClick={() => onDismiss(toast.id)} className="opacity-50 hover:opacity-100 transition-opacity">
        <X size={13} />
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message, type = "success") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {typeof document !== "undefined" &&
        createPortal(
          <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-2">
            {toasts.map((t) => (
              <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
