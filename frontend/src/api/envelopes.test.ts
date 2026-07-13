import { describe, expect, it } from 'vitest';
import { stripSuccess, unwrapData, unwrapLegacyList, unwrapPaginated } from './envelopes';

describe('unwrapData', () => {
  it('returns data from the canonical single envelope', () => {
    expect(unwrapData({ success: true, data: { id: '1', name: 'x' } })).toEqual({
      id: '1',
      name: 'x',
    });
  });

  it('strips the redundant inner success field', () => {
    expect(unwrapData({ success: true, data: { success: true, id: '1' } })).toEqual({ id: '1' });
  });

  it('passes through primitive data untouched', () => {
    expect(unwrapData({ success: true, data: 5 })).toBe(5);
  });
});

describe('unwrapPaginated', () => {
  it('normalizes the canonical paginated envelope and strips inner success', () => {
    const result = unwrapPaginated({
      success: true,
      data: [
        { success: true, id: 'a' },
        { success: true, id: 'b' },
      ],
      meta: { page: 2, limit: 10, total: 12, total_pages: 2 },
    });
    expect(result).toEqual({
      items: [{ id: 'a' }, { id: 'b' }],
      page: 2,
      limit: 10,
      total: 12,
      total_pages: 2,
    });
  });
});

describe('unwrapLegacyList', () => {
  it('normalizes the events flat list (items key)', () => {
    const result = unwrapLegacyList<{ id: string }>(
      { success: true, items: [{ id: 'e1' }], total: 1, page: 1, limit: 20, total_pages: 1 },
      'items',
    );
    expect(result.items).toEqual([{ id: 'e1' }]);
    expect(result.total).toBe(1);
  });

  it('normalizes the users flat list (users key)', () => {
    const result = unwrapLegacyList<{ id: string }>(
      { success: true, users: [{ id: 'u1' }], total: 1, page: 1, limit: 20, total_pages: 1 },
      'users',
    );
    expect(result.items).toEqual([{ id: 'u1' }]);
  });

  it('tolerates a missing list key', () => {
    const result = unwrapLegacyList(
      { success: true, total: 0, page: 1, limit: 20, total_pages: 0 },
      'items',
    );
    expect(result.items).toEqual([]);
  });
});

describe('stripSuccess', () => {
  it('unwraps the bare event object with embedded success', () => {
    expect(stripSuccess({ success: true, id: 'e1', title: 'Fest' })).toEqual({
      id: 'e1',
      title: 'Fest',
    });
  });
});
