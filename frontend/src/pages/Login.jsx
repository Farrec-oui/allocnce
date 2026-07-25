import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Plane } from "lucide-react";
import { useAuth } from "../auth";

const inputCls =
  "w-full border border-black/15 rounded-lg px-3 py-2 text-[13px] text-text bg-white focus:outline-none focus:border-primary transition-colors";

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (isAuthenticated) {
    return <Navigate to={location.state?.from ?? "/"} replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(location.state?.from ?? "/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-[380px]">
        <div className="flex flex-col items-center gap-2.5 mb-6">
          <div className="w-11 h-11 rounded-xl bg-primary flex items-center justify-center">
            <Plane size={20} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-[18px] font-semibold text-text">AllocNCE</h1>
            <p className="text-[12px] text-muted mt-0.5">Opérations EasyJet Nice</p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white border border-black/10 rounded-xl p-6 space-y-4"
        >
          <div>
            <label htmlFor="email" className="block text-[12px] font-medium text-text mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
              placeholder="vous@exemple.fr"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-[12px] font-medium text-text mb-1">
              Mot de passe
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary text-white rounded-lg text-[13px] font-medium hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {loading ? "Connexion…" : "Se connecter"}
          </button>

          {error && (
            <p role="alert" className="text-[12px] text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <p className="text-[12px] text-muted text-center pt-1">
            Pas encore de compte ?{" "}
            <Link to="/register" className="text-primary font-medium hover:underline">
              Créer un compte
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
