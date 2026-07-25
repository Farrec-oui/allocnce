import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, Inbox } from "lucide-react";
import { api } from "../api";
import { parseAllocDate } from "../utils/date";
import { useToast } from "../components/Toast";
import AllocDrawer from "../components/AllocDrawer";
import DateGroup from "../components/DateGroup";
import ModalCreate from "../components/modals/ModalCreate";
import ModalPrealloc from "../components/modals/ModalPrealloc";
import ModalUpdate from "../components/modals/ModalUpdate";

function now() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function isArchived(alloc) {
  const d = parseAllocDate(alloc.date);
  if (!d) return false;
  const cutoff = now();
  cutoff.setDate(cutoff.getDate() - 30);
  return d < cutoff;
}

const _MONS = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
function prevDayStr(dateStr) {
  const d = parseAllocDate(dateStr);
  if (!d) return null;
  d.setDate(d.getDate() - 1);
  const dd = String(d.getDate()).padStart(2, "0");
  return `${dd}${_MONS[d.getMonth()]}${String(d.getFullYear()).slice(2)}`;
}

function matchesSidebar(alloc, filter, customRange) {
  const d = parseAllocDate(alloc.date);
  if (!d) return true;
  const today = now();
  switch (filter) {
    case "today": return d.getTime() === today.getTime();
    case "tomorrow": {
      const t = new Date(today);
      t.setDate(t.getDate() + 1);
      return d.getTime() === t.getTime();
    }
    case "week": {
      const w = new Date(today);
      w.setDate(w.getDate() - 7);
      return d >= w && d <= today;
    }
    case "month": {
      const ms = new Date(today.getFullYear(), today.getMonth(), 1);
      return d >= ms;
    }
    case "custom": {
      if (!customRange.start || !customRange.end) return true;
      const s = new Date(customRange.start);
      const e = new Date(customRange.end);
      return d >= s && d <= e;
    }
    default: return true;
  }
}

export default function MesAllocs({ modal, setModal, navView, sidebarFilter, customRange }) {
  const { showToast } = useToast();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [updateTarget, setUpdateTarget] = useState(null);
  const [previewAlloc, setPreviewAlloc] = useState(null);

  const allAllocs = useMemo(() => groups.flatMap((g) => g.allocs), [groups]);

  const refresh = useCallback(async () => {
    try {
      const gs = await api.getAllocations();
      setGroups(gs);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSuccess = useCallback((msg) => {
    setModal(null);
    setUpdateTarget(null);
    showToast(msg, "success");
    refresh();
  }, [setModal, showToast, refresh]);

  const handleCloseUpdate = useCallback(() => {
    setModal(null);
    setUpdateTarget(null);
  }, [setModal]);

  const handleUpdate = useCallback((alloc) => {
    const prev = prevDayStr(alloc.date);
    const prevAllocs = allAllocs.filter((a) => a.date === prev);
    const prevId = prevAllocs.length
      ? prevAllocs.reduce((best, a) => !best || a.created_at > best.created_at ? a : best, null)?.id ?? null
      : null;
    setUpdateTarget({ allocId: alloc.id, previousDayAllocId: prevId });
  }, [allAllocs]);

  const handlePreview = useCallback((alloc) => {
    setPreviewAlloc(alloc);
  }, []);

  const handleDownload = useCallback(async (alloc) => {
    try {
      await api.downloadAllocation(alloc.id, alloc.label);
    } catch (err) {
      showToast(err.message, "error");
    }
  }, [showToast]);

  const handleDelete = useCallback(async (id, lbl) => {
    if (!confirm(`Supprimer "${lbl}" ?`)) return;
    try {
      await api.deleteAllocation(id);
      showToast("Allocation supprimée.", "success");
      refresh();
    } catch (err) {
      showToast(err.message, "error");
    }
  }, [showToast, refresh]);

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase();
    return groups
      .map(({ date, allocs }) => {
        const filtered = allocs
          .filter((a) => {
            const archived = isArchived(a);
            if (navView === "allocs"   && archived)  return false;
            if (navView === "archives" && !archived) return false;
            if (!matchesSidebar(a, sidebarFilter, customRange)) return false;
            if (q && !a.label.toLowerCase().includes(q)) return false;
            return true;
          })
          .sort((a, b) => (a.created_at > b.created_at ? 1 : -1));
        return filtered.length ? { date, allocs: filtered } : null;
      })
      .filter(Boolean)
      .sort((a, b) => {
        const da = parseAllocDate(a.date);
        const db = parseAllocDate(b.date);
        if (!da || !db) return 0;
        return db - da;
      });
  }, [groups, search, sidebarFilter, customRange, navView]);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[17px] font-semibold text-text">
            {navView === "archives" ? "Archives" : "Mes allocations"}
          </h1>
          <p className="text-[12px] text-muted mt-0.5">Gestion des allocations NCE · EasyJet</p>
        </div>
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher…"
            className="pl-8 pr-3 py-1.5 text-[13px] border border-black/15 rounded-lg bg-white focus:outline-none focus:border-primary transition-colors w-44"
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted text-[13px]">
          Chargement…
        </div>
      ) : filteredGroups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted gap-3">
          <Inbox size={36} strokeWidth={1.2} />
          <p className="text-[14px]">Aucune allocation trouvée</p>
          {navView !== "archives" && (
            <p className="text-[12px]">Créez votre première allocation avec les boutons en haut à droite.</p>
          )}
        </div>
      ) : (
        filteredGroups.map((g) => (
          <DateGroup key={g.date} group={g} onDelete={handleDelete} onUpdate={handleUpdate} onPreview={handlePreview} onDownload={handleDownload} />
        ))
      )}

      {/* Preview drawer */}
      {previewAlloc && (
        <AllocDrawer alloc={previewAlloc} onClose={() => setPreviewAlloc(null)} onDownload={handleDownload} />
      )}

      {/* Modals */}
      <ModalCreate   open={modal === "create"}   onClose={() => setModal(null)} onSuccess={handleSuccess} allocs={allAllocs} />
      <ModalPrealloc open={modal === "prealloc"} onClose={() => setModal(null)} onSuccess={handleSuccess} allocs={allAllocs} />
      <ModalUpdate
        open={modal === "update" || updateTarget !== null}
        onClose={handleCloseUpdate}
        onSuccess={handleSuccess}
        allocs={allAllocs}
        initialAllocId={updateTarget?.allocId ?? null}
        initialPreviousDayAllocId={updateTarget?.previousDayAllocId ?? null}
      />
    </div>
  );
}
