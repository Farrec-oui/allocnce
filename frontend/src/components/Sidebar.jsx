import { LayoutGrid, Archive, Calendar, X } from "lucide-react";
import clsx from "clsx";

const FILTERS = [
  { key: "today",    label: "Aujourd'hui" },
  { key: "tomorrow", label: "Demain" },
  { key: "custom",   label: "Personnalisé" },
  { key: "week",     label: "Cette semaine" },
  { key: "month",    label: "Ce mois" },
];

const inputCls = "w-full text-[11px] border border-black/15 rounded-md px-2 py-1 focus:outline-none focus:border-primary transition-colors bg-white";

export default function Sidebar({ navView, onNavView, filter, onFilter, customRange, onCustomRange }) {
  function resetCustom() {
    onFilter("all");
    onCustomRange({ start: "", end: "" });
  }

  return (
    <aside className="w-[56px] min-[900px]:w-[200px] bg-white border-r border-black/10 flex flex-col py-3 shrink-0 overflow-hidden">

      {/* Navigation */}
      <div className="px-2 min-[900px]:px-3 mb-4">
        <p className="hidden min-[900px]:block text-[10px] font-semibold text-muted uppercase tracking-wider px-2 mb-1.5">
          Navigation
        </p>
        {[
          { key: "allocs",   icon: LayoutGrid, label: "Mes allocs" },
          { key: "archives", icon: Archive,     label: "Archives" },
        ].map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            onClick={() => onNavView(key)}
            className={clsx(
              "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] transition-colors mb-0.5",
              navView === key
                ? "bg-primary-light text-primary font-medium"
                : "text-text hover:bg-surface"
            )}
          >
            <Icon size={15} className="shrink-0" />
            <span className="hidden min-[900px]:inline truncate">{label}</span>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="px-2 min-[900px]:px-3">
        <p className="hidden min-[900px]:block text-[10px] font-semibold text-muted uppercase tracking-wider px-2 mb-1.5">
          Filtres
        </p>

        {FILTERS.map(({ key, label }) => (
          <div key={key}>
            <button
              onClick={() => onFilter(filter === key ? "all" : key)}
              className={clsx(
                "w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] transition-colors mb-0.5",
                filter === key
                  ? "bg-primary-light text-primary font-medium border-l-2 border-primary"
                  : "text-muted hover:bg-surface hover:text-text"
              )}
            >
              <Calendar size={14} className="shrink-0" />
              <span className="hidden min-[900px]:inline truncate">{label}</span>
            </button>

            {/* Custom date range — revealed inline below "Personnalisé" */}
            {key === "custom" && (
              <div
                className={clsx(
                  "hidden min-[900px]:block overflow-hidden transition-all duration-200",
                  filter === "custom" ? "max-h-36 opacity-100 mb-1" : "max-h-0 opacity-0"
                )}
              >
                <div className="flex flex-col gap-1.5 px-2 pt-1">
                  <div>
                    <p className="text-[10px] text-muted mb-0.5">Du</p>
                    <input
                      type="date"
                      value={customRange.start}
                      onChange={(e) => {
                        onCustomRange({ ...customRange, start: e.target.value });
                      }}
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <p className="text-[10px] text-muted mb-0.5">Au</p>
                    <input
                      type="date"
                      value={customRange.end}
                      onChange={(e) => {
                        onCustomRange({ ...customRange, end: e.target.value });
                      }}
                      className={inputCls}
                    />
                  </div>
                  <button
                    onClick={resetCustom}
                    className="self-start text-muted hover:text-red-400 transition-colors p-0.5"
                    title="Réinitialiser"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
