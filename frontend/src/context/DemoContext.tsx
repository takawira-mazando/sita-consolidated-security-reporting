import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface DemoContextType {
  demoMode: boolean;
  toggleDemoMode: () => void;
  enableDemoMode: () => void;
  disableDemoMode: () => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);
const DEMO_MODE_DEFAULT_VERSION_KEY = 'sita_demo_mode_default_version';

export function DemoProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const search = new URLSearchParams(window.location.search);
      if (search.get('demo') === 'true' || search.get('demo') === '1' || search.get('demo') === 'on') {
        return true;
      }
    }
    if (localStorage.getItem(DEMO_MODE_DEFAULT_VERSION_KEY) !== '1') {
      return true;
    }
    const stored = localStorage.getItem('sita_demo_mode');
    return stored !== 'false';
  });

  useEffect(() => {
    localStorage.setItem(DEMO_MODE_DEFAULT_VERSION_KEY, '1');
    localStorage.setItem('sita_demo_mode', String(demoMode));
    // Sync across tabs
    window.dispatchEvent(new StorageEvent('storage', { key: 'sita_demo_mode', newValue: String(demoMode) }));
  }, [demoMode]);

  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'sita_demo_mode' && e.newValue !== null) {
        setDemoMode(e.newValue === 'true');
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const toggleDemoMode = () => setDemoMode((prev) => !prev);
  const enableDemoMode = () => setDemoMode(true);
  const disableDemoMode = () => setDemoMode(false);

  return (
    <DemoContext.Provider value={{ demoMode, toggleDemoMode, enableDemoMode, disableDemoMode }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemoMode() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemoMode must be used within a DemoProvider');
  }
  return context;
}