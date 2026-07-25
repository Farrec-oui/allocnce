import { useState } from "react";
import { api, formatAllocOption } from "../api";
import FileDropZone from "./FileDropZone";
import Modal from "./Modal";

const TYPE_LABELS = {
  prealloc:     "Pré-alloc",
  alloc_finale: "Finale",
  creation:     "Création",
  maj:          "MAJ",
};

export default function ModalUpdate({ onClose, onSuccess, allocs }) {
  const [allocId, setAllocId] = useState(allocs[0]?.id ?? "");
  const [pdfNew, setPdfNew] = useState(null);
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
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
      const n = result.new_changes_count;
      onSuccess(
        n > 0
          ? `✅ ${result.label} générée — ${n} nouveaux changements.`
          : `✅ ${result.label} générée (aucun nouveau changement).`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="🔄 Mettre à jour une allocation" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Allocation à mettre à jour <span className="text-red-500">*</span>
          </label>
          {allocs.length === 0 ? (
            <p className="text-sm text-amber-600 bg-amber-50 rounded-md px-3 py-2">
              Aucune allocation enregistrée.
            </p>
          ) : (
            <select
              required
              value={allocId}
              onChange={(e) => setAllocId(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {allocs.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.date} — {a.label} ({TYPE_LABELS[a.type] ?? a.type})
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nouveau PDF allocation <span className="text-red-500">*</span>
          </label>
          <FileDropZone label="FlightAllocationReport (mise à jour).pdf" required onChange={setPdfNew} />
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
          disabled={loading || allocs.length === 0}
          className="w-full py-2.5 bg-purple-600 text-white rounded-md font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "⏳ Génération en cours…" : "Mettre à jour"}
        </button>
      </form>
    </Modal>
  );
}
