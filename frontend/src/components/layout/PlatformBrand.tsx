interface PlatformBrandProps {
  className?: string;
  subtitle?: string;
}

export default function PlatformBrand({ className = '', subtitle }: PlatformBrandProps) {
  return (
    <span className={`platform-brand${className ? ` ${className}` : ''}`}>
      <svg className="platform-brand-shield" viewBox="0 0 32 32" aria-hidden="true">
        <path
          d="M16 2.75 4.5 7v7.5c0 7.3 4.8 12.5 11.5 15 6.7-2.5 11.5-7.7 11.5-15V7L16 2.75z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
        <path
          d="m11.5 16 3 3 6-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="platform-brand-copy">
        <strong>Unified Data Security Platform</strong>
        {subtitle && <small>{subtitle}</small>}
      </span>
    </span>
  );
}
