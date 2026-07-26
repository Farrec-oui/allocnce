import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ShieldCheck, UserCheck, UserX, UserPlus, Loader2, Pencil,
  Eye, Trash2, ChevronLeft, ChevronRight, Users, FileText, Inbox,
} from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { isoToAllocDate } from "../utils/date";
import { useToast } from "../components/Toast";
import AllocDrawer from "../components/AllocDrawer";
import ModalCreateUser from "../components/modals/ModalCreateUser";
import ModalEditUser from "../components/modals/ModalEditUser";

const PAGE_SIZE = 50;

const ROLE_CFG = {
  admin: { label: "Admin",       bg: "#E6F1FB", color: "#0C447C" },
  user:  { label: "Utilisateur", bg: "#F1EFE8", color: "#444441" },
};

const TYPE_LABELS = {
  prealloc: "Pré-alloc", alloc_finale: "Finale",
  creation: "Création", maj: "MAJ",
};

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "Z");
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const h  = String(d.getHours()).padStart(2, "0");
  const mn = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()} à ${h}h${mn}`;
}

function Badge({ cfg }) {
  return (
    <span
      className="text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
      style={{ background: cfg.bg, color: cfg.color }}
    >
      {cfg.label}
    </span>
  );
}

function StatCard({ icon, value, label }) {
  return (
    <div className="bg-white border border-black/10 rounded-xl px-4 py-3 flex items-center gap-3">
      <div className="text-primary shrink-0">{icon}</div>
      <div className="leading-tight">
        <div className="text-[18px] font-semibold text-text">{value}</div>
        <div className="text-[11px] text-muted">{label}</div>
      </div>
    </div>
  );
}

const thCls = "px-4 py-2.5 font-medium text-text text-left whitespace-nowrap";
const tdCls = "px-4 py-2.5 align-middle";
const btnCls =
  "flex items-center gap-1 px-2.5 py-1 text-[12px] rounded-lg border border-black/15 " +
  "text-text hover:bg-surface disabled:opacity-40 disabled:cursor-not-allowed " +
  "transition-colors whitespace-nowrap cursor-pointer";

function Spinner() {
  return (
    <div className="flex items-center justify-center py-20 text-muted text-[13px] gap-2">
      <Loader2 size={15} className="animate-spin" />
      Chargement…
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet Utilisateurs
// ---------------------------------------------------------------------------

function UsersTab({ me, showToast }) {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [u, s] = await Promise.all([api.listUsers(), api.adminStats()]);
      setUsers(u);
      setStats(s);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { refresh(); }, [refresh]);

  const toggleActive = useCallback(async (user) => {
    setBusyId(user.id);
    try {
      if (user.is_active) {
        await api.deactivateUser(user.id);
        showToast(`${user.full_name} désactivé.`, "success");
      } else {
        await api.updateUser(user.id, { is_active: true });
        showToast(`${user.full_name} réactivé.`, "success");
      }
      await refresh();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setBusyId(null);
    }
  }, [refresh, showToast]);

  const handleCreate = useCallback(async (payload) => {
    await api.createUser(payload);
    setCreating(false);
    showToast(`Compte ${payload.email} créé.`, "success");
    await refresh();
  }, [refresh, showToast]);

  const handleEdit = useCallback(async (id, payload) => {
    await api.updateUser(id, payload);
    setEditing(null);
    showToast("Utilisateur mis à jour.", "success");
    await refresh();
  }, [refresh, showToast]);

  if (loading) return <Spinner />;

  return (
    <>
      {stats && (
        <div className="grid gap-3 mb-5" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
          <StatCard icon={<Users size={18} />}     value={stats.total_users}        label="Utilisateurs" />
          <StatCard icon={<UserCheck size={18} />} value={stats.active_users}       label="Comptes actifs" />
          <StatCard icon={<FileText size={18} />}  value={stats.total_allocs}       label="Allocations" />
          <StatCard icon={<Inbox size={18} />}     value={stats.allocs_last_7_days} label="Depuis 7 jours" />
        </div>
      )}

      <div className="flex justify-end mb-3">
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium bg-primary text-white border border-primary hover:bg-primary-hover transition-colors cursor-pointer"
        >
          <UserPlus size={14} />
          Créer un utilisateur
        </button>
      </div>

      <div className="bg-white border border-black/10 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="bg-surface border-b border-black/10">
                <th className={thCls}>Nom</th>
                <th className={thCls}>Email</th>
                <th className={thCls}>Rôle</th>
                <th className={thCls}>Statut</th>
                <th className={thCls}>Dernière connexion</th>
                <th className={thCls}>Allocs</th>
                <th className={`${thCls} text-right`}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isMe = u.id === me?.id;
                const busy = busyId === u.id;
                return (
                  <tr key={u.id} className="border-b border-black/5 last:border-0">
                    <td className={`${tdCls} text-text`}>
                      {u.full_name}
                      {isMe && <span className="text-muted text-[11px] ml-1.5">(vous)</span>}
                    </td>
                    <td className={`${tdCls} text-muted`}>{u.email}</td>
                    <td className={tdCls}><Badge cfg={ROLE_CFG[u.role] ?? ROLE_CFG.user} /></td>
                    <td className={tdCls}>
                      <span className={u.is_active ? "text-[#27500A]" : "text-[#A32D2D]"}>
                        {u.is_active ? "Actif" : "Désactivé"}
                      </span>
                    </td>
                    <td className={`${tdCls} text-muted whitespace-nowrap`}>{fmtDateTime(u.last_login)}</td>
                    <td className={`${tdCls} text-muted`}>{u.alloc_count}</td>
                    <td className={tdCls}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button onClick={() => setEditing(u)} disabled={busy} className={btnCls}>
                          <Pencil size={13} />
                          Modifier
                        </button>
                        <button
                          onClick={() => toggleActive(u)}
                          disabled={isMe || busy}
                          title={isMe ? "Vous ne pouvez pas désactiver votre propre compte" : undefined}
                          className={`${btnCls} ${u.is_active ? "text-[#A32D2D] hover:bg-[#FCEBEB]" : ""}`}
                        >
                          {u.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                          {u.is_active ? "Désactiver" : "Réactiver"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <ModalCreateUser open={creating} onClose={() => setCreating(false)} onCreated={handleCreate} />
      <ModalEditUser
        open={editing !== null}
        user={editing}
        isSelf={editing?.id === me?.id}
        onClose={() => setEditing(null)}
        onSaved={handleEdit}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Onglet Allocations
// ---------------------------------------------------------------------------

function AllocationsTab({ showToast }) {
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState({ items: [], total: 0, offset: 0 });
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState("");
  const [date, setDate] = useState("");
  const [offset, setOffset] = useState(0);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    api.listUsers().then(setUsers).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPage(await api.adminAllocations({
        userId: userId || undefined,
        date: date ? isoToAllocDate(date) : undefined,
        limit: PAGE_SIZE,
        offset,
      }));
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  }, [userId, date, offset, showToast]);

  useEffect(() => { load(); }, [load]);

  // Tout changement de filtre ramène à la première page, sinon on peut se
  // retrouver sur un offset au-delà du nouveau total.
  const onFilterChange = (setter) => (value) => { setter(value); setOffset(0); };

  const handleDelete = useCallback(async (alloc) => {
    if (!confirm(`Supprimer définitivement « ${alloc.label} » ?\nLe fichier DOCX sera aussi effacé.`)) return;
    try {
      await api.adminDeleteAllocation(alloc.id);
      showToast("Allocation supprimée.", "success");
      await load();
    } catch (err) {
      showToast(err.message, "error");
    }
  }, [load, showToast]);

  const handleDownload = useCallback(async (alloc) => {
    try {
      await api.adminDownloadAllocation(alloc.id, alloc.label);
    } catch (err) {
      showToast(err.message, "error");
    }
  }, [showToast]);

  const pageStart = page.total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, page.total);
  const selectCls =
    "border border-black/15 rounded-lg px-3 py-1.5 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <select
          value={userId}
          onChange={(e) => onFilterChange(setUserId)(e.target.value)}
          className={selectCls}
        >
          <option value="">— Tous les utilisateurs —</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
          ))}
        </select>

        <input
          type="date"
          value={date}
          onChange={(e) => onFilterChange(setDate)(e.target.value)}
          className={selectCls}
        />

        {(userId || date) && (
          <button
            onClick={() => { setUserId(""); setDate(""); setOffset(0); }}
            className="text-[12px] text-primary hover:underline cursor-pointer"
          >
            Réinitialiser
          </button>
        )}

        <span className="text-[12px] text-muted ml-auto">
          {page.total === 0 ? "Aucune allocation" : `${pageStart}–${pageEnd} sur ${page.total}`}
        </span>
      </div>

      {loading ? <Spinner /> : (
        <div className="bg-white border border-black/10 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] border-collapse">
              <thead>
                <tr className="bg-surface border-b border-black/10">
                  <th className={thCls}>Date</th>
                  <th className={thCls}>Label</th>
                  <th className={thCls}>Type</th>
                  <th className={thCls}>Créée par</th>
                  <th className={thCls}>Créée le</th>
                  <th className={`${thCls} text-right`}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-muted text-[13px]">
                      Aucune allocation ne correspond à ces filtres.
                    </td>
                  </tr>
                ) : page.items.map((a) => (
                  <tr key={a.id} className="border-b border-black/5 last:border-0">
                    <td className={`${tdCls} text-text whitespace-nowrap`}>{a.date}</td>
                    <td className={`${tdCls} text-text`}>{a.label}</td>
                    <td className={`${tdCls} text-muted`}>{TYPE_LABELS[a.type] ?? a.type}</td>
                    <td className={`${tdCls} text-muted`}>
                      {a.user_name
                        ? <>{a.user_name}<span className="text-[11px] block">{a.user_email}</span></>
                        : <span className="italic">Sans propriétaire</span>}
                    </td>
                    <td className={`${tdCls} text-muted whitespace-nowrap`}>{fmtDateTime(a.created_at)}</td>
                    <td className={tdCls}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button onClick={() => setPreview(a)} className={btnCls}>
                          <Eye size={13} />
                          Aperçu
                        </button>
                        <button
                          onClick={() => handleDelete(a)}
                          className={`${btnCls} text-[#A32D2D] hover:bg-[#FCEBEB]`}
                        >
                          <Trash2 size={13} />
                          Supprimer
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {page.total > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className={btnCls}
          >
            <ChevronLeft size={13} />
            Précédent
          </button>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= page.total}
            className={btnCls}
          >
            Suivant
            <ChevronRight size={13} />
          </button>
        </div>
      )}

      {preview && (
        <AllocDrawer
          alloc={preview}
          admin
          onClose={() => setPreview(null)}
          onDownload={handleDownload}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------

export default function AdminPanel() {
  const { user: me } = useAuth();
  const { showToast } = useToast();
  const [tab, setTab] = useState("users");

  const tabs = useMemo(() => ([
    { id: "users",  label: "Utilisateurs" },
    { id: "allocs", label: "Allocations" },
  ]), []);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-5">
        <h1 className="text-[17px] font-semibold text-text flex items-center gap-2">
          <ShieldCheck size={17} className="text-primary" />
          Administration
        </h1>
        <p className="text-[12px] text-muted mt-0.5">
          Gestion des comptes et des allocations · tous utilisateurs
        </p>
      </div>

      <div className="flex items-center gap-1 border-b border-black/10 mb-5" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
              tab === t.id
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-text"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "users"
        ? <UsersTab me={me} showToast={showToast} />
        : <AllocationsTab showToast={showToast} />}
    </div>
  );
}
