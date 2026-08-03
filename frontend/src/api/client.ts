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
  const token = localStorage.getItem('sita_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('sita_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function handle401() {
  localStorage.removeItem('sita_token');
  localStorage.removeItem('sita_user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
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
