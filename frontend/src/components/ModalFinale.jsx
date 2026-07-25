import { useState } from "react";
import { api, formatAllocOption } from "../api";
import FileDropZone from "./FileDropZone";
import Modal from "./Modal";

export default function ModalFinale({ onClose, onSuccess, allocs }) {
  const preallocs = allocs.filter((a) => a.type === "prealloc");

  const [pdfNew, setPdfNew] = useState(null);
  const [parentId, setParentId] = useState(preallocs[0]?.id ?? "");
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedParent = allocs.find((a) => a.id === Number(parentId));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pdfNew) return setError("Veuillez sélectionner le PDF allocation.");
    if (!parentId) return setError("Veuillez sélectionner une pré-allocation de référence.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf_new", pdfNew);
      fd.append("parent_id", parentId);
      fd.append("date", selectedParent?.date ?? "");
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      const result = await api.createFinale(fd);
      const n = result.new_changes_count;
      onSuccess(
        n > 0
          ? `✅ Allocation finale générée — ${n} nouveaux changements.`
          : "✅ Allocation finale générée (aucun nouveau changement)."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="✅ Allocation finale" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nouveau PDF allocation <span className="text-red-500">*</span>
          </label>
          <FileDropZone label="FlightAllocationReport (final).pdf" required onChange={setPdfNew} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Basée sur <span className="text-red-500">*</span>
          </label>
          {preallocs.length === 0 ? (
            <p className="text-sm text-amber-600 bg-amber-50 rounded-md px-3 py-2">
              Aucune pré-allocation disponible. Créez-en une d'abord.
            </p>
          ) : (
            <select
              required
              value={parentId}
              onChange={(e) => setParentId(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {preallocs.map((a) => (
                <option key={a.id} value={a.id}>
                  {formatAllocOption(a)}
                </option>
              ))}
            </select>
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
          disabled={loading || preallocs.length === 0}
          className="w-full py-2.5 bg-indigo-600 text-white rounded-md font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "⏳ Génération en cours…" : "Générer l'allocation finale"}
        </button>
      </form>
    </Modal>
  );
}
