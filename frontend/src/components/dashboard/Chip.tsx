interface ChipProps {
  tone: 'severe' | 'high' | 'med' | 'ok' | 'closed' | 'open' | 'half';
  children: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}

const TONE_CLASS: Record<ChipProps['tone'], string> = {
  severe: 'c-severe',
  high: 'c-high',
  med: 'c-med',
  ok: 'c-ok',
  closed: 'c-closed',
  open: 'c-open',
  half: 'c-half',
};

export default function Chip({ tone, children, onClick, style }: ChipProps) {
  return (
    <span
      className={`chip ${TONE_CLASS[tone]}`}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer', ...style } : style}
    >
      {children}
    </span>
  );
}
