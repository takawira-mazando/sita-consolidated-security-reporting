import { ReactNode } from 'react';

interface DashHeaderProps {
  title: string;
  subtitle: string;
  badge: { label: string; color: string; bg: string };
  consolidatedTag: string;
  onExplain: () => void;
  onLayman: () => void;
  children?: ReactNode;
}

export default function DashHeader({
  title,
  subtitle,
  badge,
  consolidatedTag,
  onExplain,
  onLayman,
  children,
}: DashHeaderProps) {
  return (
    <div className="dash-header">
      <div>
        <div className="dash-title">
          {title}
          <small>{subtitle}</small>
        </div>
      </div>
      <span className="dash-badge" style={{ background: badge.bg, color: badge.color, border: '1px solid var(--border-dim)' }}>
        {badge.label}
      </span>
      <button className="explain-btn" onClick={onExplain}>?</button>
      <button className="layman-btn" onClick={onLayman}>Guide</button>
      <span className="consolidated-tag">{consolidatedTag}</span>
      {children}
    </div>
  );
}
