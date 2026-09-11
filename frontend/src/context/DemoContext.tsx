import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface DemoContextType {
  demoMode: boolean;
  toggleDemoMode: () => void;
  enableDemoMode: () => void;
  disableDemoMode: () => void;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoMode] = useState<boolean>(() => {
    const stored = localStorage.getItem('sita_demo_mode');
    return stored === 'true';
  });

  useEffect(() => {
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