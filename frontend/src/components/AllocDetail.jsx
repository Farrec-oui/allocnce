const TYPE_LABELS = {
  prealloc: "Pré-allocation",
  alloc_finale: "Allocation finale",
  creation: "Création",
  maj: "Mise à jour",
};

const TYPE_BADGE = {
  prealloc:     "bg-blue-100 text-blue-700",
  alloc_finale: "bg-indigo-100 text-indigo-700",
  creation:     "bg-gray-100 text-gray-600",
  maj:          "bg-purple-100 text-purple-700",
};

const HL_BADGE = [
  "bg-yellow-200 text-yellow-800",
  "bg-green-200 text-green-800",
  "bg-cyan-200 text-cyan-800",
  "bg-pink-200 text-pink-800",
];

const HL_LABEL = ["Jaune", "Vert", "Cyan", "Rose"];

function Row({ label, value }) {
  if (value == null) return null;
  return (
    <div className="flex items-start gap-2 py-2 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-400 w-28 shrink-0 pt-0.5">{label}</span>
      <span className="text-xs text-gray-800 font-medium">{value}</span>
    </div>
  );
}

export default function AllocDetail({ alloc, allAllocs, onClose }) {
  if (!alloc) return null;

  const ci = alloc.highlight_color_index % 4;
  const created = new Date(alloc.created_at + "Z").toLocaleString("fr-FR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });

  const parent = alloc.parent_id
    ? allAllocs.find((a) => a.id === alloc.parent_id)
    : null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-30"
        onClick={onClose}
      />

      {/* Sidebar */}
      <aside className="fixed top-0 right-0 h-full w-80 bg-white shadow-xl z-40 flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-800 text-sm truncate pr-2">{alloc.label}</h2>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="text-gray-400 hover:text-gray-600 text-lg leading-none shrink-0"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* Type badge */}
          <div className="flex gap-2 flex-wrap">
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${TYPE_BADGE[alloc.type] ?? "bg-gray-100 text-gray-600"}`}>
              {TYPE_LABELS[alloc.type] ?? alloc.type}
            </span>
            {alloc.changes_count > 0 && (
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${HL_BADGE[ci]}`}>
                {HL_LABEL[ci]} · {alloc.changes_count} modif.
              </span>
            )}
          </div>

          {/* Metadata */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Métadonnées</p>
            <div>
              <Row label="Date" value={alloc.date} />
              <Row label="Créé le" value={created} />
              <Row label="Modifications" value={alloc.changes_count > 0 ? `${alloc.changes_count} vol(s) surlignés` : "Aucune"} />
              {parent && <Row label="Basé sur" value={parent.label} />}
            </div>
          </div>

          {/* History chain */}
          {parent && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Historique</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0 bg-gray-50 rounded-md px-3 py-2">
                  <p className="text-xs text-gray-500 truncate">{parent.label}</p>
                  <p className="text-xs text-gray-400">{parent.date}</p>
                </div>
                <span className="text-gray-300 shrink-0">→</span>
                <div className="flex-1 min-w-0 bg-blue-50 border border-blue-200 rounded-md px-3 py-2">
                  <p className="text-xs text-blue-800 font-medium truncate">{alloc.label}</p>
                  <p className="text-xs text-blue-400">{alloc.date}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer — download */}
        <div className="px-5 py-4 border-t border-gray-200">
          {alloc.docx_url ? (
            <a
              href={`/api${alloc.docx_url}`}
              download
              className="block w-full text-center text-sm px-4 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors font-medium"
            >
              ⬇ Télécharger le DOCX
            </a>
          ) : (
            <p className="text-xs text-center text-gray-400">Pas de DOCX disponible</p>
          )}
        </div>
      </aside>
    </>
  );
}
