import { format, parseISO } from 'date-fns';

export const formatDate = (iso: string) => format(parseISO(iso), 'd MMM yyyy');

export const formatDateTime = (iso: string) => format(parseISO(iso), 'd MMM yyyy, h:mm a');

export const formatDateRange = (startIso: string, endIso: string) => {
  const start = parseISO(startIso);
  const end = parseISO(endIso);
  if (format(start, 'yyyy-MM-dd') === format(end, 'yyyy-MM-dd')) return format(start, 'd MMM yyyy');
  if (format(start, 'yyyy-MM') === format(end, 'yyyy-MM'))
    return `${format(start, 'd')}–${format(end, 'd MMM yyyy')}`;
  return `${format(start, 'd MMM')} – ${format(end, 'd MMM yyyy')}`;
};

export const toDateInputValue = (iso: string) => format(parseISO(iso), 'yyyy-MM-dd');
