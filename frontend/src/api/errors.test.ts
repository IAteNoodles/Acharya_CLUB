import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';
import { isApiError, toApiError } from './errors';

function axiosError(status: number, data: unknown, headers: Record<string, string> = {}) {
  const error = new AxiosError('Request failed', 'ERR_BAD_REQUEST');
  error.response = {
    status,
    statusText: '',
    data,
    headers,
    config: { headers: new AxiosHeaders() },
  };
  return error;
}

describe('toApiError', () => {
  it('parses the app error envelope', () => {
    const result = toApiError(
      axiosError(404, { success: false, error: { code: 'NOT_FOUND', message: 'Event not found' } }),
    );
    expect(result).toMatchObject({ status: 404, code: 'NOT_FOUND', message: 'Event not found' });
  });

  it('parses legacy HTTP_ERROR envelopes — branch on status, not code', () => {
    const result = toApiError(
      axiosError(401, {
        success: false,
        error: { code: 'HTTP_ERROR', message: 'Invalid email or password' },
      }),
    );
    expect(result.status).toBe(401);
    expect(result.code).toBe('HTTP_ERROR');
    expect(result.message).toBe('Invalid email or password');
  });

  it('maps enveloped 422 error.details into fieldErrors', () => {
    const result = toApiError(
      axiosError(422, {
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          details: [
            { loc: ['body', 'email'], msg: 'Must use a @college.edu email address', type: 'value_error' },
          ],
        },
      }),
    );
    expect(result.code).toBe('VALIDATION_ERROR');
    expect(result.fieldErrors).toEqual({ email: 'Must use a @college.edu email address' });
    expect(result.message).toBe('Must use a @college.edu email address');
  });

  it('maps enveloped details without a type field (ValidationException)', () => {
    const result = toApiError(
      axiosError(422, {
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          details: [{ loc: ['category'], msg: "must be 'participant' for out_college events" }],
        },
      }),
    );
    expect(result.fieldErrors).toEqual({ category: "must be 'participant' for out_college events" });
    expect(result.message).toBe("must be 'participant' for out_college events");
  });

  it('still maps legacy FastAPI raw 422 detail arrays into fieldErrors', () => {
    const result = toApiError(
      axiosError(422, {
        detail: [
          { loc: ['body', 'email'], msg: 'Must use a @college.edu email address', type: 'value_error' },
        ],
      }),
    );
    expect(result.code).toBe('VALIDATION_ERROR');
    expect(result.fieldErrors).toEqual({ email: 'Must use a @college.edu email address' });
    expect(result.message).toBe('Must use a @college.edu email address');
  });

  it('does not crash on a string detail', () => {
    const result = toApiError(axiosError(422, { detail: 'bad payload' }));
    expect(result.message).toBe('bad payload');
  });

  it('reads Retry-After on 429', () => {
    const result = toApiError(
      axiosError(
        429,
        { success: false, error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
        { 'retry-after': '30' },
      ),
    );
    expect(result.retryAfter).toBe(30);
  });

  it('returns a network error for failures without a response', () => {
    const result = toApiError(new AxiosError('Network Error', 'ERR_NETWORK'));
    expect(result.status).toBe(0);
    expect(result.code).toBe('NETWORK_ERROR');
  });

  it('passes through values that are already ApiError', () => {
    const original = { status: 409, code: 'CONFLICT', message: 'Already registered' };
    expect(toApiError(original)).toBe(original);
    expect(isApiError(original)).toBe(true);
  });
});
