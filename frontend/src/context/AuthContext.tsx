import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthContextType } from '../types';
import { mintDemoToken } from '../utils/jwt';

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  login: async () => ({ ok: true }),
  logout: () => {},
});

export const DEMO_ACCOUNTS: {
  email: string;
  label: string;
  role: string;
  password: string;
}[] = [
  { email: 'exec@example.com', label: 'Executive', role: 'exec', password: 'pass123' },
  { email: 'soc@example.com', label: 'SOC Analyst', role: 'soc', password: 'pass123' },
  { email: 'appsec@example.com', label: 'AppSec', role: 'appsec', password: 'pass123' },
  { email: 'dbsec@example.com', label: 'DB Security', role: 'dbsec', password: 'pass123' },
  { email: 'compliance@example.com', label: 'Compliance', role: 'compliance', password: 'pass123' },
  { email: 'sre@example.com', label: 'Service Ops', role: 'sre', password: 'pass123' },
];

export const ADMIN_EMAIL = 'admin@example.com';
export const ADMIN_PASSWORD = 'admin123';
export const USER_PASSWORD = 'pass123';

export const ALL_ROLES = ['exec', 'soc', 'appsec', 'dbsec', 'compliance', 'sre'];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('sita_user');
    if (stored) {
      try {
        const restored = JSON.parse(stored) as User;
        setUser(restored);
        if (!localStorage.getItem('sita_token')) {
          localStorage.setItem(
            'sita_token',
            mintDemoToken({ sub: restored.sub, email: restored.email, roles: restored.roles })
          );
        }
      } catch {
        localStorage.removeItem('sita_user');
      }
    }
    setIsLoading(false);
  }, []);

  const storeSession = (u: User) => {
    const token = mintDemoToken({ sub: u.sub, email: u.email, roles: u.roles });
    localStorage.setItem('sita_token', token);
    localStorage.setItem('sita_user', JSON.stringify(u));
  };

  const login = async (email?: string, password?: string): Promise<{ ok: boolean; error?: string }> => {
    const normalized = (email || '').trim().toLowerCase();
    const pass = password || '';

    if (normalized === ADMIN_EMAIL) {
      if (pass !== ADMIN_PASSWORD) {
        return { ok: false, error: 'Wrong admin password.' };
      }
      const adminUser: User = {
        sub: 'admin',
        email: normalized,
        roles: ALL_ROLES,
        name: 'Admin',
      };
      storeSession(adminUser);
      setUser(adminUser);
      return { ok: true };
    }

    const account = DEMO_ACCOUNTS.find((a) => a.email === normalized);
    if (!account) {
      return { ok: false, error: 'Unknown email. Use one of the demo addresses below.' };
    }
    if (pass !== USER_PASSWORD) {
      return { ok: false, error: 'Wrong password (hint: pass123).' };
    }
    const demoUser: User = {
      sub: `user_${account.role}`,
      email: normalized,
      roles: [account.role],
      name: account.label,
    };
    storeSession(demoUser);
    setUser(demoUser);
    return { ok: true };
  };

  const logout = () => {
    localStorage.removeItem('sita_user');
    localStorage.removeItem('sita_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
