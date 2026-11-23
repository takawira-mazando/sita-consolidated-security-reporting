import { useNavigate } from 'react-router-dom';

interface DemoDirectorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DemoDirectorModal({ isOpen, onClose }: DemoDirectorModalProps) {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const continueToSignIn = () => {
    onClose();
    navigate('/login');
  };

  return (
    <div
      className="login-overlay as-modal"
      style={{ zIndex: 9999, backdropFilter: 'blur(8px)' }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="platform-explore-title"
        className="login-card"
        style={{
          position: 'relative',
          width: 'min(440px, 92vw)',
          padding: '32px',
          borderRadius: 18,
          textAlign: 'left',
        }}
      >
        <button
          type="button"
          className="overlay-close"
          onClick={onClose}
          aria-label="Close"
          style={{ position: 'absolute', top: 16, right: 18, fontSize: 22 }}
        >
          &times;
        </button>
        <p style={{ margin: '0 0 8px', color: 'var(--accent)', fontSize: 11, fontWeight: 700, letterSpacing: '.1em', textTransform: 'uppercase' }}>
          Security intelligence
        </p>
        <h2 id="platform-explore-title" style={{ margin: '0 28px 10px 0', fontSize: 25, fontFamily: 'Space Grotesk, sans-serif' }}>
          See the platform in action
        </h2>
        <p style={{ margin: '0 0 22px', color: 'var(--text-muted)', fontSize: 14, lineHeight: 1.6 }}>
          Connect security signals to portfolio risk, priority actions, and compliance posture.
        </p>
        <button type="button" className="btn btn-flare" onClick={continueToSignIn} style={{ width: '100%' }}>
          Continue to sign in
        </button>
        <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 12, textAlign: 'center' }}>
          Demo workspaces are available on the sign-in page.
        </p>
      </section>
    </div>
  );
}
