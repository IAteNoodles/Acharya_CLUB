import { isAxiosError } from 'axios';

export interface ApiError {
  status: number;
  code: string;
  message: string;
  fieldErrors?: Record<string, string>;
  retryAfter?: number;
}

export function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === 'object' &&
    value !== null &&
    !(value instanceof Error) &&
    typeof (value as ApiError).status === 'number' &&
    typeof (value as ApiError).code === 'string' &&
    typeof (value as ApiError).message === 'string'
  );
}

interface FastApiDetailItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) return error;

  if (!isAxiosError(error) || !error.response) {
    return {
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Could not reach the server. Check your connection and try again.',
    };
  }

  const { status, data, headers } = error.response;
  const result: ApiError = {
    status,
    code: 'HTTP_ERROR',
    message: 'Something went wrong. Try again.',
  };

  const retryAfter = Number(headers?.['retry-after']);
  if (!Number.isNaN(retryAfter) && retryAfter > 0) result.retryAfter = retryAfter;

  if (data && typeof data === 'object') {
    if ('error' in data && data.error && typeof data.error === 'object') {
      const err = data.error as { code?: string; message?: string };
      if (err.code) result.code = err.code;
      if (err.message) result.message = err.message;
      return result;
    }
    if ('detail' in data) {
      result.code = 'VALIDATION_ERROR';
      if (Array.isArray(data.detail)) {
        const fieldErrors: Record<string, string> = {};
        for (const item of data.detail as FastApiDetailItem[]) {
          const field = item.loc?.filter((part) => part !== 'body').join('.') || 'form';
          fieldErrors[field] = item.msg;
        }
        result.fieldErrors = fieldErrors;
        result.message = Object.values(fieldErrors)[0] ?? 'Check the highlighted fields.';
      } else if (typeof data.detail === 'string') {
        result.message = data.detail;
      }
      return result;
    }
  }

  return result;
}
