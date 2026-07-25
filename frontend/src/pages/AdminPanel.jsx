import { useCallback, useEffect, useState } from "react";
import { ShieldCheck, UserCheck, UserX, Loader2 } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../components/Toast";

function fmt(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "Z");
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const h  = String(d.getHours()).padStart(2, "0");
  const mn = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()} à ${h}h${mn}`;
}

const ROLE_CFG = {
  admin: { label: "Admin", bg: "#EAF3DE", color: "#27500A" },
  user:  { label: "Utilisateur", bg: "#F1EFE8", color: "#444441" },
};

export default function AdminPanel() {
  const { user: me } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setUsers(await api.listUsers());
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { refresh(); }, [refresh]);

  const patch = useCallback(async (id, payload, successMsg) => {
    setBusyId(id);
    try {
      await api.updateUser(id, payload);
      showToast(successMsg, "success");
      await refresh();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setBusyId(null);
    }
  }, [refresh, showToast]);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-[17px] font-semibold text-text flex items-center gap-2">
          <ShieldCheck size={17} className="text-primary" />
          Administration
        </h1>
        <p className="text-[12px] text-muted mt-0.5">Gestion des comptes utilisateurs</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-muted text-[13px] gap-2">
          <Loader2 size={15} className="animate-spin" />
          Chargement…
        </div>
      ) : (
        <div className="bg-white border border-black/10 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px] border-collapse">
              <thead>
                <tr className="bg-surface border-b border-black/10 text-left">
                  <th className="px-4 py-2.5 font-medium text-text">Nom</th>
                  <th className="px-4 py-2.5 font-medium text-text">Email</th>
                  <th className="px-4 py-2.5 font-medium text-text">Rôle</th>
                  <th className="px-4 py-2.5 font-medium text-text">Statut</th>
                  <th className="px-4 py-2.5 font-medium text-text whitespace-nowrap">
                    Dernière connexion
                  </th>
                  <th className="px-4 py-2.5 font-medium text-text text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isMe = u.id === me?.id;
                  const role = ROLE_CFG[u.role] ?? ROLE_CFG.user;
                  const busy = busyId === u.id;
                  return (
                    <tr key={u.id} className="border-b border-black/5 last:border-0">
                      <td className="px-4 py-2.5 text-text">
                        {u.full_name}
                        {isMe && <span className="text-muted text-[11px] ml-1.5">(vous)</span>}
                      </td>
                      <td className="px-4 py-2.5 text-muted">{u.email}</td>
                      <td className="px-4 py-2.5">
                        <span
                          className="text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
                          style={{ background: role.bg, color: role.color }}
                        >
                          {role.label}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={u.is_active ? "text-[#27500A]" : "text-[#A32D2D]"}>
                          {u.is_active ? "Actif" : "Désactivé"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-muted whitespace-nowrap">
                        {fmt(u.last_login)}
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            disabled={isMe || busy}
                            onClick={() =>
                              patch(
                                u.id,
                                { role: u.role === "admin" ? "user" : "admin" },
                                `${u.full_name} est désormais ${u.role === "admin" ? "utilisateur" : "administrateur"}.`
                              )
                            }
                            title={isMe ? "Vous ne pouvez pas modifier votre propre rôle" : undefined}
                            className="px-2.5 py-1 text-[12px] rounded-lg border border-black/15 text-text hover:bg-surface disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                          >
                            {u.role === "admin" ? "Retirer admin" : "Promouvoir admin"}
                          </button>
                          <button
                            disabled={isMe || busy}
                            onClick={() =>
                              patch(
                                u.id,
                                { is_active: !u.is_active },
                                `${u.full_name} ${u.is_active ? "désactivé" : "réactivé"}.`
                              )
                            }
                            title={isMe ? "Vous ne pouvez pas désactiver votre propre compte" : undefined}
                            className={`flex items-center gap-1 px-2.5 py-1 text-[12px] rounded-lg border transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap ${
                              u.is_active
                                ? "border-black/15 text-[#A32D2D] hover:bg-[#FCEBEB]"
                                : "border-black/15 text-text hover:bg-surface"
                            }`}
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
      )}
    </div>
  );
}
