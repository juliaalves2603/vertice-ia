import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import MetricCard from "../components/MetricCard";
import api from "../services/api";

export default function Dashboard() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    api
      .get("/api/session-check")
      .then((res) => setSession(res.data))
      .catch((err) => {
        console.error(err);
        setSession({
          status: "offline",
          error: err.message,
        });
      });
  }, []);

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        background: "#f4f6f8",
      }}
    >
      <Sidebar />

      <main
        style={{
          flex: 1,
          padding: "40px",
        }}
      >
        <Header />

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
            gap: "20px",
          }}
        >
          <MetricCard title="Seguidores" value="--" />
          <MetricCard title="Alcance" value="--" />
          <MetricCard title="Impressões" value="--" />
          <MetricCard title="Visitas ao Perfil" value="--" />
          <MetricCard title="Engajamento" value="--" />
        </div>

        <div
          style={{
            marginTop: "40px",
            background: "#fff",
            padding: "20px",
            borderRadius: "12px",
            boxShadow: "0 2px 8px rgba(0,0,0,.08)",
          }}
        >
          <h3>Status da API</h3>

          <pre>
            {JSON.stringify(session, null, 2)}
          </pre>
        </div>
      </main>
    </div>
  );
}