import { Route, Routes, Navigate } from "react-router-dom";
import { AuthProvider, RequireAuth } from "./components/Auth";
import { MetaProvider, useMeta } from "./components/Meta";
import Layout from "./components/Layout";
import { ErrorBox } from "./components/ui";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Vehicles from "./pages/Vehicles";
import Analysis from "./pages/Analysis";
import MLModel from "./pages/MLModel";

function MetaGate({ children }) {
  const { error } = useMeta();
  return error ? <div className="mx-auto max-w-lg p-8"><ErrorBox>{error}</ErrorBox></div> : children;
}

export default function App() {
  return (
    <AuthProvider>
      <MetaProvider>
        <MetaGate>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<RequireAuth><Layout /></RequireAuth>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/vehicles" element={<Vehicles />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/ml" element={<MLModel />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MetaGate>
      </MetaProvider>
    </AuthProvider>
  );
}
