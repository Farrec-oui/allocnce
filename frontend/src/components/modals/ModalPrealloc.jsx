import { useMemo, useState } from "react";
import { api, formatAllocOption } from "../../api";
import { parseAllocDate } from "../../utils/date";
import DropZone from "../DropZone";
import ModalBase from "./ModalBase";

const label = (text, required) => (
  <label className="block text-[12px] font-medium text-text mb-1">
    {text}{required && <span className="text-red-500 ml-0.5">*</span>}
  </label>
);

const selectCls = "w-full border border-black/15 rounded-lg px-3 py-2 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

export default function ModalPrealloc({ open, onClose, onSuccess, allocs = [] }) {
  const sorted = useMemo(() =>
    [...allocs].sort((a, b) =>
      parseAllocDate(b.date) - parseAllocDate(a.date) ||
      new Date(b.created_at) - new Date(a.created_at)
    ), [allocs]);

  const [pdfAlloc, setPdfAlloc] = useState(null);
  const [pdfFj, setPdfFj] = useState(null);
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!pdfAlloc) return setError("Veuillez sélectionner le PDF allocation.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf_alloc", pdfAlloc);
      if (pdfFj) fd.append("pdf_fj", pdfFj);
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      const result = await api.createPrealloc(fd);
      const hl = result.changes_count;
      onSuccess(hl > 0 ? `Pré-allocation générée — ${hl} modifications surlignées.` : "Pré-allocation générée.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalBase open={open} onClose={onClose} title="Pré-allocation" subtitle="Comparaison avec la feuille de journée">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          {label("PDF allocation EasyJet", true)}
          <DropZone label="FlightAllocationReport.pdf" onChange={setPdfAlloc} />
        </div>

        <div>
          {label("Feuille de journée")}
          <p className="text-[11px] text-muted -mt-0.5 mb-1">Optionnel — active la comparaison et le surlignage</p>
          <DropZone label="Feuille de journée MZS.pdf" onChange={setPdfFj} />
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
          type="submit" disabled={loading}
          className="w-full py-2.5 bg-primary text-white rounded-lg text-[13px] font-medium hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {loading ? "Génération en cours…" : "Générer la pré-allocation"}
        </button>
      </form>
    </ModalBase>
  );
}
