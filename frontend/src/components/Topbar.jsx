import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FilePlus, FileText, RefreshCw, Plane, LogOut, ShieldCheck, ChevronDown } from "lucide-react";
import { useAuth } from "../auth";

function Btn({ onClick, primary, icon, children }) {
  const base = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors border cursor-pointer";
  const style = primary
    ? "bg-primary text-white border-primary hover:bg-primary-hover"
    : "bg-white text-text border-black/15 hover:bg-surface";

  return (
    <button onClick={onClick} className={`${base} ${style}`}>
      {icon}
      <span className="hidden min-[900px]:inline">{children}</span>
    </button>
  );
}

function initials(name = "") {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

function UserMenu() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  if (!user) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 pl-1.5 pr-2 py-1 rounded-lg hover:bg-surface transition-colors cursor-pointer"
      >
        <div className="w-6 h-6 rounded-full bg-primary text-white text-[10px] font-semibold flex items-center justify-center shrink-0">
          {initials(user.full_name)}
        </div>
        <span className="hidden min-[900px]:inline text-[13px] text-text max-w-[150px] truncate">
          {user.full_name}
        </span>
        <ChevronDown size={13} className="text-muted shrink-0" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-[calc(100%+6px)] w-56 bg-white border border-black/10 rounded-xl shadow-lg py-1 z-50"
        >
          <div className="px-3 py-2 border-b border-black/8">
            <div className="text-[13px] font-medium text-text truncate">{user.full_name}</div>
            <div className="text-[11px] text-muted truncate">{user.email}</div>
            {isAdmin && (
              <span className="inline-block mt-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[#EAF3DE] text-[#27500A]">
                Administrateur
              </span>
            )}
          </div>

          {isAdmin && (
            <Link
              to="/admin"
              onClick={() => setOpen(false)}
              role="menuitem"
              className="flex items-center gap-2 w-full px-3 py-2 text-[13px] text-text hover:bg-surface transition-colors"
            >
              <ShieldCheck size={14} />
              Administration
            </Link>
          )}

          <button
            onClick={handleLogout}
            role="menuitem"
            className="flex items-center gap-2 w-full px-3 py-2 text-[13px] text-[#A32D2D] hover:bg-[#FCEBEB] transition-colors cursor-pointer"
          >
            <LogOut size={14} />
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}

export default function Topbar({ onOpenModal, showActions = true }) {
  return (
    <header className="h-[52px] bg-white border-b border-black/10 flex items-center justify-between px-4 shrink-0 z-10">
      <Link to="/" className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center shrink-0">
          <Plane size={13} className="text-white" />
        </div>
        <div className="leading-none">
          <div className="text-[15px] font-semibold text-text">AllocNCE</div>
          <div className="text-[11px] text-muted mt-0.5">Opérations EasyJet Nice</div>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        {showActions && (
          <>
            <Btn onClick={() => onOpenModal("create")} icon={<FilePlus size={14} />}>
              Créer
            </Btn>
            <Btn onClick={() => onOpenModal("prealloc")} icon={<FileText size={14} />}>
              Pré-allocation
            </Btn>
            <Btn onClick={() => onOpenModal("update")} primary icon={<RefreshCw size={14} />}>
              Mettre à jour
            </Btn>
          </>
        )}
        <div className="w-px h-6 bg-black/10 mx-1" />
        <UserMenu />
      </div>
    </header>
  );
}
