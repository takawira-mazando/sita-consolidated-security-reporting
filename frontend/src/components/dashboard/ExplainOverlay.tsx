interface ExplainOverlayProps {
  open: boolean;
  title: string;
  body: string;
  onClose: () => void;
}

export default function ExplainOverlay({ open, title, body, onClose }: ExplainOverlayProps) {
  if (!open) return null;
  return (
    <div className="overlay open" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="overlay-content" onClick={(e) => e.stopPropagation()}>
        <div className="overlay-close" onClick={onClose}>✕</div>
        <div className="overlay-title">{title}</div>
        <div className="overlay-body" dangerouslySetInnerHTML={{ __html: body }} />
      </div>
    </div>
  );
}
