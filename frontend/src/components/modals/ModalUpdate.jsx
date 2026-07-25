import { useEffect, useMemo, useState } from "react";
import { api, formatAllocOption } from "../../api";
import { parseAllocDate } from "../../utils/date";
import DropZone from "../DropZone";
import ModalBase from "./ModalBase";

const TYPE_LABELS = { prealloc:"Pré-alloc", alloc_finale:"Finale", creation:"Création", maj:"MAJ" };

const label = (text, required) => (
  <label className="block text-[12px] font-medium text-text mb-1">
    {text}{required && <span className="text-red-500 ml-0.5">*</span>}
  </label>
);

const selectCls = "w-full border border-black/15 rounded-lg px-3 py-2 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

export default function ModalUpdate({ open, onClose, onSuccess, allocs = [], initialAllocId = null, initialPreviousDayAllocId = null }) {
  const sorted = useMemo(() =>
    [...allocs].sort((a, b) =>
      parseAllocDate(b.date) - parseAllocDate(a.date) ||
      new Date(b.created_at) - new Date(a.created_at)
    ), [allocs]);

  const [allocId, setAllocId] = useState(initialAllocId ?? allocs[0]?.id ?? "");
  const [pdfNew, setPdfNew] = useState(null);
  const [previousDayAllocId, setPreviousDayAllocId] = useState(initialPreviousDayAllocId ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setAllocId(initialAllocId ?? allocs[0]?.id ?? "");
      setPreviousDayAllocId(initialPreviousDayAllocId ?? "");
      setPdfNew(null);
      setError(null);
    }
  }, [open, initialAllocId, initialPreviousDayAllocId]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!allocId) return setError("Veuillez sélectionner une allocation.");
    if (!pdfNew) return setError("Veuillez sélectionner le nouveau PDF.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf_new", pdfNew);
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      const result = await api.updateWithPdf(allocId, fd);
      const n = result.changes_count;
      onSuccess(n > 0 ? `${result.label} mise à jour — ${n} nouveaux changements.` : `${result.label} mise à jour.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalBase open={open} onClose={onClose} title="Mettre à jour" subtitle="Comparer et régénérer une allocation">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          {label("Allocation à mettre à jour", true)}
          {allocs.length === 0 ? (
            <p className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Aucune allocation enregistrée.
            </p>
          ) : (
            <select required value={allocId} onChange={(e) => setAllocId(e.target.value)} className={selectCls}>
              {sorted.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.date} — {a.label} ({TYPE_LABELS[a.type] ?? a.type})
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          {label("Nouveau PDF allocation", true)}
          <DropZone label="FlightAllocationReport (mise à jour).pdf" onChange={setPdfNew} />
        </div>

        <div>
          {label("Alloc de la veille")}
          <p className="text-[11px] text-muted -mt-0.5 mb-1">Pour peupler le tableau Night Stop J/J+1</p>
          <select value={previousDayAllocId} onChange={(e) => setPreviousDayAllocId(e.target.value)} className={selectCls}>
            <option value="">— Non renseigné —</option>
            {sorted.map((a) => <option key={a.id} value={a.id}>{formatAllocOption(a)}</option>)}
          </select>
        </div>

        {error && <p className="text-[12px] text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        <button
          type="submit" disabled={loading || allocs.length === 0}
          className="w-full py-2.5 bg-primary text-white rounded-lg text-[13px] font-medium hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {loading ? "Génération en cours…" : "Mettre à jour"}
        </button>
      </form>
    </ModalBase>
  );
}
