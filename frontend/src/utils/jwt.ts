function b64url(obj: unknown): string {
  const json = JSON.stringify(obj);
  const bytes = new TextEncoder().encode(json);
  let bin = '';
  bytes.forEach((b) => {
    bin += String.fromCharCode(b);
  });
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function mintDemoToken(
  payload: { sub: string; email: string; roles: string[] },
  ttlSeconds = 12 * 3600
): string {
  const header = { alg: 'HS256', typ: 'JWT' };
  const body = {
    ...payload,
    aud: '',
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
  };
  return `${b64url(header)}.${b64url(body)}.${b64url({ demo: true })}`;
}
