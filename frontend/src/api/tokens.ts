const REFRESH_TOKEN_KEY = 'acharya.refreshToken';

let accessToken: string | null = null;
let onSessionExpired: (() => void) | null = null;
let onAccessTokenChanged: ((token: string | null) => void) | null = null;

export const tokens = {
  getAccess: () => accessToken,
  setAccess(token: string | null) {
    accessToken = token;
    onAccessTokenChanged?.(token);
  },
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setRefresh(token: string | null) {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
    else localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  clear() {
    tokens.setAccess(null);
    tokens.setRefresh(null);
  },
  registerSessionExpiredHandler(handler: () => void) {
    onSessionExpired = handler;
  },
  registerAccessTokenListener(listener: (token: string | null) => void) {
    onAccessTokenChanged = listener;
  },
  notifySessionExpired() {
    onSessionExpired?.();
  },
};
