import api from './client';
import type { NarrativeFacts, PlatformModel } from '../types';

export async function fetchPlatformModel(): Promise<PlatformModel> {
  const { data } = await api.get('/meta/model');
  return data;
}

export async function fetchNarrativeFacts(): Promise<NarrativeFacts> {
  const { data } = await api.get('/meta/narrative-facts');
  return data;
}