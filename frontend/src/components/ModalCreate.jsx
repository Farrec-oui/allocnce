import { useState } from "react";
import { api, toAllocDate, formatAllocOption } from "../api";
import FileDropZone from "./FileDropZone";
import Modal from "./Modal";

const today = () => new Date().toISOString().split("T")[0];

export default function ModalCreate({ onClose, onSuccess, allocs = [] }) {
  const [pdf, setPdf] = useState(null);
  const [date, setDate] = useState(today());
  const [previousDayAllocId, setPreviousDayAllocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pdf) return setError("Veuillez sélectionner un PDF.");
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("pdf", pdf);
      fd.append("date", toAllocDate(date));
      if (previousDayAllocId) fd.append("previous_day_alloc_id", previousDayAllocId);
      await api.createAllocation(fd);
      onSuccess("✅ Allocation générée !");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title="➕ Créer une allocation" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PDF allocation EasyJet <span className="text-red-500">*</span>
          </label>
          <FileDropZone label="FlightAllocationReport.pdf" required onChange={setPdf} />
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
          {loading ? "⏳ Génération en cours…" : "Créer"}
        </button>
      </form>
    </Modal>
  );
}
