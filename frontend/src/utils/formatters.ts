export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-ZA', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-ZA', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatNumber(n: number): string {
  return n.toLocaleString('en-ZA');
}

export function formatPercent(n: number): string {
  return `${n.toFixed(1)}%`;
}
