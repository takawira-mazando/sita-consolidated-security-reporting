import api from './client';
import type { User } from '../types';

export interface LoginResponse {
  token: string;
  user: User;
}

export interface DemoAccount {
  email: string;
  label: string;
  role: string;
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', { email, password });
  return data;
}

export async function demoLoginRequest(role: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/demo-login', { role });
  return data;
}

export async function fetchDemoAccounts(): Promise<DemoAccount[]> {
  const { data } = await api.get<DemoAccount[]>('/auth/demo-accounts');
  return data;
}
