import AllocCard from "./AllocCard";

function fmtGroupDate(s) {
  const MONS = { JAN:"JAN",FEB:"FÉV",MAR:"MAR",APR:"AVR",MAY:"MAI",JUN:"JUN",JUL:"JUL",AUG:"AOÛ",SEP:"SEP",OCT:"OCT",NOV:"NOV",DEC:"DÉC" };
  const m = s?.match(/(\d{2})([A-Z]{3})(\d{2})/);
  if (!m) return s;
  return `${m[1]} ${MONS[m[2]] ?? m[2]} 20${m[3]}`;
}

export default function DateGroup({ group, onDelete, onUpdate, onPreview, onDownload }) {
  const { date, allocs } = group;
  const latestId = allocs.reduce((best, a) =>
    !best || a.created_at > best.created_at ? a : best, null
  )?.id;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-[12px] font-semibold text-muted uppercase tracking-wide bg-surface border border-black/10 px-2.5 py-0.5 rounded-full">
          {fmtGroupDate(date)}
        </span>
        <div className="flex-1 h-px bg-black/8" />
        <span className="text-[11px] text-muted">{allocs.length} alloc{allocs.length > 1 ? "s" : ""}</span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: "12px",
        }}
      >
        {allocs.map((a) => (
          <AllocCard key={a.id} alloc={a} isLatest={a.id === latestId} onDelete={onDelete} onUpdate={onUpdate} onPreview={onPreview} onDownload={onDownload} />
        ))}
      </div>
    </div>
  );
}
