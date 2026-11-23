import { useState, useEffect } from 'react';

const STORAGE_KEY = 'platform_active_client_name';
const EVENT_NAME = 'platform_client_name_changed';

/**
 * Returns the active Client Organization Name.
 * If not explicitly saved in localStorage, checks the first active tenant in
 * Defaults to the provisioned client organization.
 */
export function getClientOrgName(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored.trim()) {
      return stored.trim();
    }

  } catch (error) {
    console.warn('Unable to read the active client name from local storage.', error);
  }

  // Fallback: no tenants provisioned yet — show the Operator platform name
  return 'Hosi Technologies';
}

/**
 * Sets the active Client Organization Name, persists to localStorage,
 * and notifies all components via a browser event.
 */
export function setClientOrgName(name: string): void {
  const trimmed = name.trim();
  if (!trimmed) return;
  try {
    localStorage.setItem(STORAGE_KEY, trimmed);
  } catch (error) {
    console.warn('Unable to save the active client name to local storage.', error);
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: trimmed }));
  }
}

/**
 * React hook that subscribes to dynamic client organization name updates.
 */
export function useClientOrgName(): [string, (name: string) => void] {
  const [clientOrgName, setOrgNameState] = useState<string>(() => getClientOrgName());

  useEffect(() => {
    const handleUpdate = () => {
      setOrgNameState(getClientOrgName());
    };
    window.addEventListener(EVENT_NAME, handleUpdate);
    window.addEventListener('storage', handleUpdate);
    return () => {
      window.removeEventListener(EVENT_NAME, handleUpdate);
      window.removeEventListener('storage', handleUpdate);
    };
  }, []);

  return [clientOrgName, setClientOrgName];
}
