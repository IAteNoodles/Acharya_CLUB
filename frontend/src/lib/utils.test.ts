import { describe, expect, it } from 'vitest';
import { eventDays } from './utils';

describe('eventDays', () => {
  it('produces one entry per calendar day, inclusive', () => {
    const days = eventDays('2026-08-01T00:00:00', '2026-08-03T00:00:00');
    expect(days).toHaveLength(3);
    expect(days[0]).toEqual({ index: 1, date: '2026-08-01', label: 'Day 1' });
    expect(days[2]).toEqual({ index: 3, date: '2026-08-03', label: 'Day 3' });
  });

  it('handles single-day events', () => {
    expect(eventDays('2026-08-01T09:00:00', '2026-08-01T18:00:00')).toHaveLength(1);
  });

  it('never returns fewer than one day even if end precedes start', () => {
    expect(eventDays('2026-08-02T00:00:00', '2026-08-01T00:00:00')).toHaveLength(1);
  });
});
