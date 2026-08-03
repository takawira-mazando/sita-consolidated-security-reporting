interface GaugeProps {
  pct: number;
  label: string;
  color: string;
  sublabel?: string;
}

export default function Gauge({ pct, label, color, sublabel }: GaugeProps) {
  return (
    <div className="gauge-wrap">
      <div
        className="gauge-ring"
        style={{
          background: `conic-gradient(${color} 0% ${pct}%, var(--surface-3) ${pct}% 100%)`,
        }}
      >
        <div className="inner">
          <span className="pct" style={{ color }}>{pct}%</span>
          <span className="lbl">{label}</span>
        </div>
      </div>
      {sublabel && <div className="gauge-lbl">{sublabel}</div>}
    </div>
  );
}
