import type { Paginated } from '@/types/domain';

function stripInnerSuccess<T>(value: T): T {
  if (value && typeof value === 'object' && !Array.isArray(value) && 'success' in value) {
    const { success: _ignored, ...rest } = value as Record<string, unknown>;
    return rest as T;
  }
  return value;
}

export function unwrapData<T>(body: { success: boolean; data: T }): T {
  return stripInnerSuccess(body.data);
}

export function unwrapPaginated<T>(body: {
  success: boolean;
  data: T[];
  meta: { page: number; limit: number; total: number; total_pages: number };
}): Paginated<T> {
  return {
    items: body.data.map(stripInnerSuccess),
    page: body.meta.page,
    limit: body.meta.limit,
    total: body.meta.total,
    total_pages: body.meta.total_pages,
  };
}

export function unwrapLegacyList<T>(
  body: Record<string, unknown> & {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  },
  key: 'items' | 'users',
): Paginated<T> {
  return {
    items: ((body[key] ?? []) as T[]).map(stripInnerSuccess),
    page: body.page,
    limit: body.limit,
    total: body.total,
    total_pages: body.total_pages,
  };
}

export function stripSuccess<T>(body: Record<string, unknown>): T {
  const { success: _ignored, ...rest } = body;
  return rest as T;
}
