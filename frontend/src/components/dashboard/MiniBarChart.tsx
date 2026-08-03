interface MiniBarChartProps {
  bars: { height: string; color: string }[];
  axis?: string[];
  height?: number;
  paired?: boolean;
}

export default function MiniBarChart({ bars, axis, height = 100, paired }: MiniBarChartProps) {
  if (paired) {
    const groups: { height: string; color: string }[][] = [];
    for (let i = 0; i < bars.length; i += 2) {
      groups.push([bars[i], bars[i + 1]].filter(Boolean));
    }
    return (
      <div>
        <div className="mini-bar-chart" style={{ height }}>
          {groups.map((group, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                justifyContent: 'flex-end',
              }}
            >
              {group.map((b, j) => (
                <div
                  key={j}
                  style={{ height: b.height, background: b.color, borderRadius: '3px 3px 0 0' }}
                />
              ))}
            </div>
          ))}
        </div>
        {axis && <div className="chart-axis">{axis.map((a, i) => <span key={i}>{a}</span>)}</div>}
      </div>
    );
  }
  return (
    <div>
      <div className="mini-bar-chart" style={{ height }}>
        {bars.map((b, i) => (
          <div key={i} className="b" style={{ height: b.height, background: b.color }} />
        ))}
      </div>
      {axis && <div className="chart-axis">{axis.map((a, i) => <span key={i}>{a}</span>)}</div>}
    </div>
  );
}
