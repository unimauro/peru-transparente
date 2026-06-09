// Fondo decorativo: malla de "red de poder" con nodos y aristas (incluye hipótesis punteadas).
export function NetworkHero() {
  const nodes = [
    { x: 70, y: 28, r: 7, c: "#e11d2a" },
    { x: 88, y: 16, r: 4, c: "#4f8cff" },
    { x: 92, y: 40, r: 5, c: "#a78bfa" },
    { x: 60, y: 46, r: 4, c: "#4f8cff" },
    { x: 96, y: 26, r: 3, c: "#22d3ee" },
    { x: 80, y: 58, r: 5, c: "#22d3ee" },
    { x: 50, y: 22, r: 3, c: "#22c55e" },
  ];
  const edges = [[0, 1], [0, 2], [0, 3], [2, 4], [2, 5], [3, 6], [1, 4], [5, 3]];
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-70" viewBox="0 0 100 70" preserveAspectRatio="xMaxYMid slice">
      <g stroke="#2a3447" strokeWidth="0.25">
        {edges.map(([a, b], i) => (
          <line key={i} x1={nodes[a].x} y1={nodes[a].y} x2={nodes[b].x} y2={nodes[b].y} />
        ))}
      </g>
      <line x1={nodes[5].x} y1={nodes[5].y} x2={60} y2={64} stroke="#f59e0b" strokeWidth="0.3" strokeDasharray="1 1.2" />
      {nodes.map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r={n.r / 2 + 1.5} fill={n.c} opacity="0.18">
            <animate attributeName="r" values={`${n.r / 2 + 1.2};${n.r / 2 + 2.4};${n.r / 2 + 1.2}`} dur={`${3 + i * 0.4}s`} repeatCount="indefinite" />
          </circle>
          <circle cx={n.x} cy={n.y} r={n.r / 2.4} fill={n.c} />
        </g>
      ))}
    </svg>
  );
}
