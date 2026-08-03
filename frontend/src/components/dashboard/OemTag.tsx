const OEM_CLASS: Record<string, string> = {
  appscan: 'oem-appscan',
  imperva: 'oem-imperva',
  'imperva-waf': 'oem-imperva-waf',
  'api-sec': 'oem-api-sec',
  compliance: 'oem-compliance',
};

export default function OemTag({ source, label }: { source: string; label?: string }) {
  const cls = OEM_CLASS[source] || 'oem-appscan';
  return <span className={`oem-src ${cls}`}>{label || source}</span>;
}
