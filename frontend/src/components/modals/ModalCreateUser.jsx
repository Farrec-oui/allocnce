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

export default function ModalCreateUser({ open, onClose, onCreated }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("user");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      setEmail(""); setFullName(""); setRole("user");
      setPassword(""); setError(null);
    }
  }, [open]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password.length < MIN_PASSWORD) {
      return setError(`Le mot de passe doit faire au moins ${MIN_PASSWORD} caractères.`);
    }
    setLoading(true);
    setError(null);
    try {
      await onCreated({
        email: email.trim(),
        full_name: fullName.trim(),
        role,
        password,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalBase
      open={open}
      onClose={onClose}
      title="Créer un utilisateur"
      subtitle="Le compte est actif immédiatement"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          {label("Nom complet", true)}
          <input
            type="text" required autoFocus value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={inputCls} placeholder="Jean Dupont"
          />
        </div>

        <div>
          {label("Email", true)}
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputCls} placeholder="jean.dupont@exemple.fr"
          />
        </div>

        <div>
          {label("Rôle", true)}
          <select value={role} onChange={(e) => setRole(e.target.value)} className={inputCls}>
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
        </div>

        <div>
          {label("Mot de passe", true)}
          <input
            type="password" required minLength={MIN_PASSWORD}
            autoComplete="new-password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputCls} placeholder="8 caractères minimum"
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
          {loading ? "Création…" : "Créer le compte"}
        </button>
      </form>
    </ModalBase>
  );
}
