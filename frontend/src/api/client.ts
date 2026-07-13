import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { toApiError } from './errors';
import { tokens } from './tokens';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const client = axios.create({ baseURL: API_BASE_URL });

const AUTH_PATHS = ['/auth/login', '/auth/signup', '/auth/refresh'];

let refreshInFlight: Promise<string> | null = null;

async function performRefresh(): Promise<string> {
  const refreshToken = tokens.getRefresh();
  if (!refreshToken) throw new Error('No refresh token');
  const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refreshToken });
  const pair = res.data.data as { accessToken: string; refreshToken: string };
  tokens.setRefresh(pair.refreshToken);
  tokens.setAccess(pair.accessToken);
  return pair.accessToken;
}

export function refreshSession(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

client.interceptors.request.use((config) => {
  const token = tokens.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
  const status = error.response?.status;
  const isAuthPath = AUTH_PATHS.some((path) => config?.url?.includes(path));

  if (status === 401 && config && !config._retried && !isAuthPath) {
    config._retried = true;
    try {
      const newToken = await refreshSession();
      config.headers.Authorization = `Bearer ${newToken}`;
      return client(config);
    } catch {
      tokens.clear();
      tokens.notifySessionExpired();
      throw toApiError(error);
    }
  }

  throw toApiError(error);
});
