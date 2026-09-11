import api from './client';
import { useDemoMode } from '../context/DemoContext';
import { useAuth } from '../hooks/useAuth';

const DEMO_DEPARTMENT_ID = 'home-affairs-digital';

let demoModeEnabled = false;

export function setDemoModeInterceptor(enabled: boolean) {
  demoModeEnabled = enabled;
}

export function isDemoModeInterceptorEnabled(): boolean {
  return demoModeEnabled;
}

function demoErrorResponse(error: any): Promise<never> {
  return Promise.reject(error);
}

export function setupDemoInterceptor() {
  // Request interceptor: add demo tenant filter when in demo mode
  api.interceptors.request.use((config) => {
    if (!demoModeEnabled) return config;

    const url = config.url || '';
    const method = config.method?.toLowerCase() || 'get';

    // For GET requests to findings, metrics, risks, compliance - add demo tenant filter
    if (method === 'get') {
      const params = config.params || {};
      
      // Add demo department filter to all relevant endpoints
      if (
        url.includes('/findings') ||
        url.includes('/metrics') ||
        url.includes('/risks') ||
        url.includes('/risk-scores') ||
        url.includes('/compliance') ||
        url.includes('/dashboard') ||
        url.includes('/public/summary')
      ) {
        // The backend tenant_filter will automatically apply based on user's department_ids
        // But we can also explicitly pass a filter
        config.params = {
          ...params,
          department_id: DEMO_DEPARTMENT_ID,
          _demo: 'true',
        };
      }
    }

    return config;
  });

  // Response interceptor: transform demo data if needed
  api.interceptors.response.use(
    (response) => {
      if (!demoModeEnabled) return response;
      
      // Optionally transform response for demo mode
      // e.g., prefix app names, add demo indicators
      return response;
    },
    (error) => Promise.reject(error)
  );
}

// Hook to sync demo mode with interceptor
export function useDemoInterceptor() {
  const { demoMode } = useDemoMode();
  
  if (typeof window !== 'undefined') {
    setDemoModeInterceptor(demoMode);
  }
  
  return demoMode;
}

// Alternative: API functions that explicitly query demo data
export const demoApi = {
  async getDemoFindings(params?: any) {
    return api.get('/findings', { 
      params: { 
        ...params, 
        department_id: DEMO_DEPARTMENT_ID,
        _demo: 'true' 
      } 
    });
  },
  
  async getDemoMetrics() {
    return Promise.all([
      api.get('/metrics/fix-rate', { params: { department_id: DEMO_DEPARTMENT_ID } }),
      api.get('/metrics/waf-summary', { params: { department_id: DEMO_DEPARTMENT_ID } }),
      api.get('/metrics/api-exposure', { params: { department_id: DEMO_DEPARTMENT_ID } }),
    ]);
  },
  
  async getDemoRisks() {
    return api.get('/risks', { params: { department_id: DEMO_DEPARTMENT_ID } });
  },
  
  async getDemoCompliance() {
    return api.get('/compliance', { params: { department_id: DEMO_DEPARTMENT_ID } });
  },
  
  async getDemoPublicSummary() {
    return api.get('/public/summary', { params: { department_id: DEMO_DEPARTMENT_ID } });
  },
};