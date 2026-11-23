import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

export const adminApi = axios.create({
  baseURL: '/admin',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('platform_token');
  const tenantWorkspaceId = localStorage.getItem('platform_active_tenant_workspace');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (tenantWorkspaceId) {
    config.headers['X-Tenant-Workspace-ID'] = tenantWorkspaceId;
  } else {
    delete config.headers['X-Tenant-Workspace-ID'];
  }
  return config;
});

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('platform_token');
  const tenantWorkspaceId = localStorage.getItem('platform_active_tenant_workspace');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (tenantWorkspaceId) {
    config.headers['X-Tenant-Workspace-ID'] = tenantWorkspaceId;
  } else {
    delete config.headers['X-Tenant-Workspace-ID'];
  }
  return config;
});

function handle401() {
  localStorage.removeItem('platform_token');
  localStorage.removeItem('platform_user');
  if (window.location.pathname !== '/') {
    window.location.href = '/';
  }
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      handle401();
    }
    return Promise.reject(error);
  }
);

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      handle401();
    }
    return Promise.reject(error);
  }
);

export default api;
