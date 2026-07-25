import { useState } from "react";
import { api, toAllocDate, formatAllocOption } from "../api";
import FileDropZone from "./FileDropZone";
import Modal from "./Modal";

const today = () => new Date().toISOString().split("T")[0];

export default function ModalPrealloc({ onClose, onSuccess, allocs = [] }) {
  const [pdfAlloc, setPdfAlloc] = useState(null);
  const [pdfFj, setPdfFj] = useState(null);
  const [date, setDate] = useState(today());
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pdfAlloc) return setError("Veuillez sélectionner le PDF allocation.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf_alloc", pdfAlloc);
      if (pdfFj) fd.append("pdf_fj", pdfFj);
      fd.append("date", toAllocDate(date));
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      const result = await api.createPrealloc(fd);
      const hl = result.highlights_count;
      onSuccess(
        hl > 0
          ? `✅ Pré-allocation générée — ${hl} modifications surlignées.`
          : "✅ Pré-allocation générée."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="📋 Pré-allocation" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PDF allocation EasyJet <span className="text-red-500">*</span>
          </label>
          <FileDropZone label="FlightAllocationReport.pdf" required onChange={setPdfAlloc} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Feuille de journée{" "}
            <span className="text-gray-400 font-normal">(optionnel — active la comparaison)</span>
          </label>
          <FileDropZone label="Feuille de journée MZS.pdf" onChange={setPdfFj} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {date && (
            <p className="text-xs text-gray-400 mt-1">Identifiant : {toAllocDate(date)}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Alloc de la veille{" "}
            <span className="text-gray-400 font-normal">(pour le tableau Night Stop)</span>
          </label>
          <select
            value={previousDayAllocId}
            onChange={(e) => setPreviousDayAllocId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— Non renseigné (tableau vide) —</option>
            {allocs.map((a) => (
              <option key={a.id} value={a.id}>
                {formatAllocOption(a)}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "⏳ Génération en cours…" : "Générer la pré-allocation"}
        </button>
      </form>
    </Modal>
  );
}
