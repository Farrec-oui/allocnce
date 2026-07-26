import { useEffect, useState } from "react";
import ModalBase from "./ModalBase";

const MIN_PASSWORD = 8;

const inputCls =
  "w-full border border-black/15 rounded-lg px-3 py-2 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

const label = (text, required) => (
  <label className="block text-[12px] font-medium text-text mb-1">
    {text}{required && <span className="text-red-500 ml-0.5">*</span>}
  </label>
);

export default function ModalEditUser({ open, user, isSelf, onClose, onSaved }) {
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("user");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && user) {
      setFullName(user.full_name);
      setRole(user.role);
      setPassword("");
      setError(null);
    }
  }, [open, user]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password && password.length < MIN_PASSWORD) {
      return setError(`Le mot de passe doit faire au moins ${MIN_PASSWORD} caractères.`);
    }
    setLoading(true);
    setError(null);
    try {
      // Le mot de passe n'est envoyé que s'il a été saisi : le laisser vide
      // conserve l'actuel. Le rôle est omis pour son propre compte, le backend
      // le refuserait de toute façon.
      const payload = { full_name: fullName.trim() };
      if (!isSelf) payload.role = role;
      if (password) payload.password = password;
      await onSaved(user.id, payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!user) return null;

  return (
    <ModalBase open={open} onClose={onClose} title="Modifier l'utilisateur" subtitle={user.email}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          {label("Nom complet", true)}
          <input
            type="text" required autoFocus value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={inputCls}
          />
        </div>

        <div>
          {label("Rôle")}
          <select
            value={role} disabled={isSelf}
            onChange={(e) => setRole(e.target.value)}
            className={`${inputCls} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
          {isSelf && (
            <p className="text-[11px] text-muted mt-1">
              Vous ne pouvez pas modifier votre propre rôle.
            </p>
          )}
        </div>

        <div>
          {label("Nouveau mot de passe")}
          <input
            type="password" minLength={MIN_PASSWORD}
            autoComplete="new-password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputCls} placeholder="Laisser vide pour ne pas changer"
          />
        </div>

        {error && (
          <p role="alert" className="text-[12px] text-red-600 bg-red-50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit" disabled={loading}
          className="w-full py-2.5 bg-primary text-white rounded-lg text-[13px] font-medium hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {loading ? "Enregistrement…" : "Enregistrer"}
        </button>
      </form>
    </ModalBase>
  );
}
