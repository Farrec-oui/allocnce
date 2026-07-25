import { useState } from "react";
import { api, formatAllocOption } from "../../api";
import DropZone from "../DropZone";
import ModalBase from "./ModalBase";

const label = (text, required) => (
  <label className="block text-[12px] font-medium text-text mb-1">
    {text}{required && <span className="text-red-500 ml-0.5">*</span>}
  </label>
);

const selectCls = "w-full border border-black/15 rounded-lg px-3 py-2 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

export default function ModalFinale({ open, onClose, onSuccess, allocs = [] }) {
  const preallocs = allocs.filter((a) => a.type === "prealloc");
  const [pdfNew, setPdfNew] = useState(null);
  const [parentId, setParentId] = useState(preallocs[0]?.id ?? "");
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!pdfNew) return setError("Veuillez sélectionner le PDF allocation.");
    if (!parentId) return setError("Veuillez sélectionner une pré-allocation de référence.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf_new", pdfNew);
      fd.append("parent_id", parentId);
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      const result = await api.createFinale(fd);
      const n = result.changes_count;
      onSuccess(n > 0 ? `Allocation finale générée — ${n} nouveaux changements.` : "Allocation finale générée.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalBase open={open} onClose={onClose} title="Allocation finale" subtitle="Basée sur une pré-allocation existante">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          {label("PDF allocation finale", true)}
          <DropZone label="FlightAllocationReport (final).pdf" onChange={setPdfNew} />
        </div>

        <div>
          {label("Pré-allocation de référence", true)}
          {preallocs.length === 0 ? (
            <p className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Aucune pré-allocation disponible. Créez-en une d'abord.
            </p>
          ) : (
            <select required value={parentId} onChange={(e) => setParentId(e.target.value)} className={selectCls}>
              {preallocs.map((a) => <option key={a.id} value={a.id}>{formatAllocOption(a)}</option>)}
            </select>
          )}
        </div>

        <div>
          {label("Alloc de la veille")}
          <p className="text-[11px] text-muted -mt-0.5 mb-1">Pour peupler le tableau Night Stop J/J+1</p>
          <select value={previousDayAllocId} onChange={(e) => setPreviousDayAllocId(e.target.value)} className={selectCls}>
            <option value="">— Non renseigné —</option>
            {allocs.map((a) => <option key={a.id} value={a.id}>{formatAllocOption(a)}</option>)}
          </select>
        </div>

        {error && <p className="text-[12px] text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        <button
          type="submit" disabled={loading || preallocs.length === 0}
          className="w-full py-2.5 bg-primary text-white rounded-lg text-[13px] font-medium hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {loading ? "Génération en cours…" : "Générer l'allocation finale"}
        </button>
      </form>
    </ModalBase>
  );
}
