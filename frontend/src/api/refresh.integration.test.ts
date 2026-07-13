import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { appError, BASE, legacyList, STUDENT } from '@/test/msw/fixtures';
import { server } from '@/test/msw/server';
import { useAuthStore } from '@/stores/auth.store';
import { client } from './client';
import { isApiError } from './errors';
import { tokens } from './tokens';

function installRotatingBackend() {
  let refreshCalls = 0;
  let validAccess = new Set(['access-valid']);
  let validRefresh = 'refresh-1';

  server.use(
    http.post(`${BASE}/auth/refresh`, async ({ request }) => {
      refreshCalls += 1;
      const body = (await request.json()) as { refreshToken: string };
      if (body.refreshToken !== validRefresh) {
        return HttpResponse.json(appError('HTTP_ERROR', 'Invalid refresh token'), { status: 401 });
      }
      // rotation: old refresh token is blacklisted, a new pair is issued
      validRefresh = `refresh-${refreshCalls + 1}`;
      const newAccess = `access-${refreshCalls + 1}`;
      validAccess = new Set([newAccess]);
      return HttpResponse.json({
        success: true,
        data: { accessToken: newAccess, refreshToken: validRefresh },
      });
    }),
    http.get(`${BASE}/events`, ({ request }) => {
      const auth = request.headers.get('authorization') ?? '';
      const token = auth.replace('Bearer ', '');
      if (!validAccess.has(token)) {
        return HttpResponse.json(appError('HTTP_ERROR', 'Could not validate credentials'), {
          status: 401,
        });
      }
      return HttpResponse.json(legacyList('items', []));
    }),
  );

  return { getRefreshCalls: () => refreshCalls };
}

describe('refresh single-flight', () => {
  it('serializes parallel 401s into exactly one refresh and retries both requests', async () => {
    const backend = installRotatingBackend();
    tokens.setAccess('access-expired');
    tokens.setRefresh('refresh-1');

    const [a, b] = await Promise.all([client.get('/events'), client.get('/events')]);
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    expect(backend.getRefreshCalls()).toBe(1);
    expect(tokens.getRefresh()).toBe('refresh-2');
    expect(tokens.getAccess()).toBe('access-2');
  });

  it('hard-logs-out when the refresh itself fails', async () => {
    installRotatingBackend();
    useAuthStore.setState({ status: 'authed', sessionExpired: false });
    tokens.setAccess('access-expired');
    tokens.setRefresh('refresh-stale');

    await expect(client.get('/events')).rejects.toMatchObject({ status: 401 });
    expect(tokens.getRefresh()).toBeNull();
    expect(tokens.getAccess()).toBeNull();
    expect(useAuthStore.getState().status).toBe('guest');
    expect(useAuthStore.getState().sessionExpired).toBe(true);
  });

  it('does not attempt refresh for auth endpoints', async () => {
    const backend = installRotatingBackend();
    server.use(
      http.post(`${BASE}/auth/login`, () =>
        HttpResponse.json(appError('HTTP_ERROR', 'Invalid email or password'), { status: 401 }),
      ),
    );
    tokens.setRefresh('refresh-1');

    await expect(
      client.post('/auth/login', { email: 'x@college.edu', password: 'nope' }),
    ).rejects.toMatchObject({ status: 401 });
    expect(backend.getRefreshCalls()).toBe(0);
  });

  it('surfaces normalized ApiError objects from the interceptor', async () => {
    server.use(
      http.get(`${BASE}/events`, () =>
        HttpResponse.json(appError('FORBIDDEN', 'Not allowed'), { status: 403 }),
      ),
    );
    tokens.setAccess('anything');
    try {
      await client.get('/events');
      expect.unreachable('request should have failed');
    } catch (error) {
      expect(isApiError(error)).toBe(true);
      expect(error).toMatchObject({ status: 403, code: 'FORBIDDEN', message: 'Not allowed' });
    }
  });
});

describe('session bootstrap', () => {
  it('restores the session from a stored refresh token', async () => {
    installRotatingBackend();
    server.use(
      http.get(`${BASE}/auth/me`, () =>
        HttpResponse.json({ success: true, data: { user: STUDENT } }),
      ),
    );
    tokens.setRefresh('refresh-1');
    useAuthStore.setState({ status: 'booting' });

    await useAuthStore.getState().bootstrap();
    const state = useAuthStore.getState();
    expect(state.status).toBe('authed');
    expect(state.user?.email).toBe(STUDENT.email);
    expect(tokens.getRefresh()).toBe('refresh-2');
  });

  it('lands as guest when no refresh token exists', async () => {
    useAuthStore.setState({ status: 'booting' });
    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('guest');
  });

  it('clears a stale refresh token and lands as guest', async () => {
    installRotatingBackend();
    tokens.setRefresh('refresh-stale');
    useAuthStore.setState({ status: 'booting' });

    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('guest');
    expect(tokens.getRefresh()).toBeNull();
  });
});
