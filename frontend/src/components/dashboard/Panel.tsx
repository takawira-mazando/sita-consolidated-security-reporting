import { ReactNode } from 'react';

interface PanelProps {
  title?: ReactNode;
  hint?: ReactNode;
  children: ReactNode;
  bodyClassName?: string;
  bodyStyle?: React.CSSProperties;
  headerRight?: ReactNode;
}

export default function Panel({
  title,
  hint,
  children,
  bodyClassName,
  bodyStyle,
  headerRight,
}: PanelProps) {
  return (
    <div className="panel">
      {title && (
        <div className="panel-h">
          {title}
          {headerRight}
          {hint && <span className="hint">{hint}</span>}
        </div>
      )}
      <div className={bodyClassName ? `panel-b ${bodyClassName}` : 'panel-b'} style={bodyStyle}>
        {children}
      </div>
    </div>
  );
}
