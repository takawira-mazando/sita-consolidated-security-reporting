import { ReactNode } from 'react';

interface StatCardProps {
  ghost: string;
  accent: string;
  value: string;
  valueColor?: string;
  label: ReactNode;
  delta?: ReactNode;
  deltaColor?: string;
}

export default function StatCard({
  ghost,
  accent,
  value,
  valueColor,
  label,
  delta,
  deltaColor,
}: StatCardProps) {
  return (
    <div className="stat-card" data-ghost={ghost}>
      <div className="stat-accent" style={{ background: accent }} />
      <div className="stat-n" style={valueColor ? { color: valueColor } : undefined}>{value}</div>
      <div className="stat-l">{label}</div>
      {delta && (
        <div className="stat-delta" style={deltaColor ? { color: deltaColor } : undefined}>
          {delta}
        </div>
      )}
    </div>
  );
}
