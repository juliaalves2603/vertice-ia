export default function App() {
  return (
    <div
      style={{
        background: "#0B0B0B",
        color: "#FFFFFF",
        minHeight: "100vh",
        padding: "40px",
        fontFamily: "Arial"
      }}
    >
      <h1>VÉRTICE IA</h1>

      <h2>Dashboard 1.0</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5,1fr)",
          gap: "20px",
          marginTop: "30px"
        }}
      >
        <Card titulo="Seguidores" />
        <Card titulo="Alcance" />
        <Card titulo="Impressões" />
        <Card titulo="Visitas" />
        <Card titulo="Engajamento" />
      </div>
    </div>
  );
}

function Card({ titulo }) {
  return (
    <div
      style={{
        background: "#1A1A1A",
        borderRadius: "12px",
        padding: "20px"
      }}
    >
      <h3>{titulo}</h3>
      <h1>--</h1>
    </div>
  );
}