export default function Sidebar() {
  const items = [
    "Dashboard",
    "Clientes",
    "Relatórios",
    "Insights IA",
    "Configurações",
  ];

  return (
    <aside
      style={{
        width: 240,
        background: "#111827",
        color: "#fff",
        padding: 24,
      }}
    >
      <h2 style={{ marginBottom: 40 }}>VÉRTICE IA</h2>

      {items.map((item) => (
        <div
          key={item}
          style={{
            padding: "12px 0",
            cursor: "pointer",
          }}
        >
          {item}
        </div>
      ))}
    </aside>
  );
}