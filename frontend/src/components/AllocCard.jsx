import { Download, Eye, RefreshCw, Trash2, Clock } from "lucide-react";
import clsx from "clsx";

const TYPE_CFG = {
  prealloc:     { label: "Pré-alloc",  bg: "#FAEEDA", color: "#633806" },
  alloc_finale: { label: "Finale",     bg: "#EAF3DE", color: "#27500A" },
  maj:          { label: "MAJ",        bg: "#E6F1FB", color: "#0C447C" },
  creation:     { label: "Création",   bg: "#F1EFE8", color: "#444441" },
};

const HL_COLORS = ["#EAB308", "#22C55E", "#06B6D4", "#EC4899"];

function fmtDate(iso) {
  const d = new Date(iso + "Z");
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const h  = String(d.getHours()).padStart(2, "0");
  const mn = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm} à ${h}h${mn}`;
}

export default function AllocCard({ alloc, isLatest, onDelete, onUpdate, onPreview, onDownload }) {
  const cfg = TYPE_CFG[alloc.type] ?? TYPE_CFG.creation;
  const ci  = alloc.highlight_color_index ?? 0;
  const n   = alloc.changes_count ?? 0;

  return (
    <div
      className={clsx(
        "bg-white rounded-xl flex flex-col gap-3 transition-shadow hover:shadow-md",
        "border p-[14px_16px]",
        isLatest ? "border-primary shadow-sm" : "border-black/15"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-[14px] font-medium text-text leading-snug">{alloc.label}</span>
        <span
          className="text-[11px] font-medium px-2 py-0.5 rounded-full shrink-0 whitespace-nowrap"
          style={{ background: cfg.bg, color: cfg.color }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Created at */}
      <div className="flex items-center gap-1.5 text-[12px] text-muted">
        <Clock size={11} className="shrink-0" />
        <span>Créée le {fmtDate(alloc.created_at)}</span>
      </div>

      {/* Highlight indicator */}
      {n > 0 && (
        <div className="flex items-center gap-1.5">
          <div
            className="w-2 h-2 rounded-[2px] shrink-0"
            style={{ background: HL_COLORS[ci % 4] }}
          />
          <span className="text-[12px] text-muted">
            {n} modification{n > 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Footer — grille 2×2 */}
      <div className="border-t border-black/8 pt-2.5 grid grid-cols-2 gap-1.5">
        <button
          onClick={() => onPreview(alloc)}
          className="flex items-center justify-center gap-1.5 min-h-[36px] px-3.5 text-[13px] font-medium rounded-lg border border-black/15 text-text hover:bg-surface transition-colors"
        >
          <Eye size={16} />
          Aperçu
        </button>
        <button
          onClick={() => onUpdate(alloc)}
          className="flex items-center justify-center gap-1.5 min-h-[36px] px-3.5 text-[13px] font-medium rounded-lg border border-black/15 text-text hover:bg-surface transition-colors"
        >
          <RefreshCw size={16} />
          Mettre à jour
        </button>
        {/* Bouton et non <a download> : la route exige un en-tête
            Authorization, qu'une navigation par lien ne peut pas porter. */}
        <button
          onClick={() => onDownload(alloc)}
          className="flex items-center justify-center gap-1.5 min-h-[36px] px-3.5 text-[13px] font-medium rounded-lg border border-black/15 text-text hover:bg-surface transition-colors"
        >
          <Download size={16} />
          Télécharger
        </button>
        <button
          onClick={() => onDelete(alloc.id, alloc.label)}
          className="flex items-center justify-center gap-1.5 min-h-[36px] px-3.5 text-[13px] font-medium rounded-lg border border-black/15 text-[#A32D2D] hover:bg-[#FCEBEB] transition-colors"
        >
          <Trash2 size={16} />
          Supprimer
        </button>
      </div>
    </div>
  );
}
