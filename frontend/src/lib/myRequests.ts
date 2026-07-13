const storageKey = (userId: string) => `acharya.myEventRequests.${userId}`;

export function myEventRequestIds(userId: string): string[] {
  try {
    const raw = localStorage.getItem(storageKey(userId));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : [];
  } catch {
    return [];
  }
}

export function rememberMyEventRequest(userId: string, eventId: string) {
  const ids = myEventRequestIds(userId);
  if (!ids.includes(eventId)) {
    localStorage.setItem(storageKey(userId), JSON.stringify([eventId, ...ids]));
  }
}
