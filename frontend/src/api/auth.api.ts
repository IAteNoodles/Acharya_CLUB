import type { Role } from '@/types/enums';
import type { User } from '@/types/domain';
import { client } from './client';
import { unwrapData } from './envelopes';

export interface AuthPayload {
  user: User;
  accessToken: string;
  refreshToken: string;
}

export interface SignupInput {
  name: string;
  email: string;
  password: string;
  role: Extract<Role, 'student' | 'teacher'>;
}

export const signup = (input: SignupInput) =>
  client.post('/auth/signup', input).then((r) => unwrapData<AuthPayload>(r.data));

export const login = (email: string, password: string) =>
  client.post('/auth/login', { email, password }).then((r) => unwrapData<AuthPayload>(r.data));

export const logout = (refreshToken: string) =>
  client.post('/auth/logout', { refreshToken }).then((r) => unwrapData<{ message: string }>(r.data));

export const me = () =>
  client.get('/auth/me').then((r) => unwrapData<{ user: User }>(r.data).user);
