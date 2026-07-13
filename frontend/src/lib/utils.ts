import { clsx, type ClassValue } from 'clsx';
import { addDays, differenceInCalendarDays, format, parseISO } from 'date-fns';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface EventDay {
  index: number;
  date: string;
  label: string;
}

export function eventDays(startIso: string, endIso: string): EventDay[] {
  const start = parseISO(startIso);
  const end = parseISO(endIso);
  const count = Math.max(0, differenceInCalendarDays(end, start)) + 1;
  return Array.from({ length: count }, (_, i) => ({
    index: i + 1,
    date: format(addDays(start, i), 'yyyy-MM-dd'),
    label: `Day ${i + 1}`,
  }));
}
