interface BarRowProps {
  label: React.ReactNode;
  width: string;
  color: string;
  value: string;
}

export default function BarRow({ label, width, color, value }: BarRowProps) {
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width, background: color }} />
      </div>
      <span className="bar-val">{value}</span>
    </div>
  );
}
