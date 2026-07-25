import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { AuthProvider, useAuth } from "./auth";
import { ToastProvider } from "./components/Toast";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";
import MesAllocs from "./pages/MesAllocs";
import AdminPanel from "./pages/AdminPanel";
import Login from "./pages/Login";
import Register from "./pages/Register";

function FullPageSpinner() {
  return (
    <div className="h-screen flex items-center justify-center bg-surface text-muted gap-2 text-[13px]">
      <Loader2 size={16} className="animate-spin" />
      Chargement…
    </div>
  );
}

/** Bloque l'accès tant que l'utilisateur n'est pas authentifié. */
function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullPageSpinner />;
  if (!isAuthenticated) {
    // `from` permet de revenir sur la page demandée après connexion.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

function RequireAdmin({ children }) {
  const { isAdmin, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

/** Page principale : Topbar + Sidebar + liste des allocations. */
function AllocsPage() {
  const [modal, setModal] = useState(null);
  const [navView, setNavView] = useState("allocs");
  const [sidebarFilter, setSidebarFilter] = useState("all");
  const [customRange, setCustomRange] = useState({ start: "", end: "" });

  return (
    <div className="h-screen flex flex-col bg-surface overflow-hidden">
      <Topbar onOpenModal={setModal} />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          navView={navView}
          onNavView={setNavView}
          filter={sidebarFilter}
          onFilter={setSidebarFilter}
          customRange={customRange}
          onCustomRange={setCustomRange}
        />
        <MesAllocs
          modal={modal}
          setModal={setModal}
          navView={navView}
          sidebarFilter={sidebarFilter}
          customRange={customRange}
        />
      </div>
    </div>
  );
}

function AdminPage() {
  return (
    <div className="h-screen flex flex-col bg-surface overflow-hidden">
      <Topbar showActions={false} />
      <div className="flex flex-1 min-h-0">
        <AdminPanel />
      </div>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AllocsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireAdmin>
              <AdminPage />
            </RequireAdmin>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
