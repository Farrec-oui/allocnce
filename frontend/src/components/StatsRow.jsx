function StatCard({ value, label, accent }) {
  return (
    <div className="bg-white rounded-xl border border-black/10 px-4 py-3.5">
      <div className="text-2xl font-semibold" style={{ color: accent }}>{value ?? 0}</div>
      <div className="text-[12px] text-muted mt-0.5">{label}</div>
    </div>
  );
}

export default function StatsRow({ stats }) {
  return (
    <div className="grid grid-cols-2 min-[900px]:grid-cols-4 gap-3 mb-6">
      <StatCard value={stats?.total}                label="Total"         accent="#185FA5" />
      <StatCard value={stats?.by_type?.prealloc}    label="Pré-allocs"    accent="#633806" />
      <StatCard value={stats?.by_type?.alloc_finale}label="Finales"       accent="#27500A" />
      <StatCard value={stats?.by_type?.maj ?? 0}    label="Mises à jour"  accent="#0C447C" />
    </div>
  );
}
