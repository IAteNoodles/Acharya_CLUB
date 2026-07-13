import { create } from 'zustand';
import * as authApi from '@/api/auth.api';
import { refreshSession } from '@/api/client';
import { tokens } from '@/api/tokens';
import type { User } from '@/types/domain';

export type SessionStatus = 'booting' | 'authed' | 'guest';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  status: SessionStatus;
  sessionExpired: boolean;
  bootstrap(): Promise<void>;
  login(email: string, password: string): Promise<User>;
  signup(input: authApi.SignupInput): Promise<{ user: User; enteredApp: boolean }>;
  logout(): Promise<void>;
  clearSession(expired?: boolean): void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  status: 'booting',
  sessionExpired: false,

  async bootstrap() {
    if (!tokens.getRefresh()) {
      set({ status: 'guest' });
      return;
    }
    try {
      await refreshSession();
      const user = await authApi.me();
      set({ user, status: 'authed', sessionExpired: false });
    } catch {
      tokens.clear();
      set({ user: null, accessToken: null, status: 'guest' });
    }
  },

  async login(email, password) {
    const { user, accessToken, refreshToken } = await authApi.login(email, password);
    tokens.setAccess(accessToken);
    tokens.setRefresh(refreshToken);
    set({ user, status: 'authed', sessionExpired: false });
    return user;
  },

  async signup(input) {
    const { user, accessToken, refreshToken } = await authApi.signup(input);
    if (user.role === 'teacher') {
      return { user, enteredApp: false };
    }
    tokens.setAccess(accessToken);
    tokens.setRefresh(refreshToken);
    set({ user, status: 'authed', sessionExpired: false });
    return { user, enteredApp: true };
  },

  async logout() {
    const refreshToken = tokens.getRefresh();
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // clearing the local session is what matters; the server token expires on its own
      }
    }
    get().clearSession();
  },

  clearSession(expired = false) {
    tokens.clear();
    set({ user: null, accessToken: null, status: 'guest', sessionExpired: expired });
  },
}));

tokens.registerAccessTokenListener((token) => {
  useAuthStore.setState({ accessToken: token });
});

tokens.registerSessionExpiredHandler(() => {
  useAuthStore.setState({ user: null, accessToken: null, status: 'guest', sessionExpired: true });
});
