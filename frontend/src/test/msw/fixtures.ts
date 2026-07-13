export const BASE = 'http://localhost:8000/api/v1';

export const STUDENT = {
  id: '11111111-1111-4111-8111-111111111111',
  name: 'Sita Sharma',
  email: 'sita@college.edu',
  role: 'student',
  status: 'active',
};

export const TEACHER = {
  id: '22222222-2222-4222-8222-222222222222',
  name: 'Prof. Rao',
  email: 'rao@college.edu',
  role: 'teacher',
  status: 'active',
};

export const PENDING_TEACHER = {
  id: '33333333-3333-4333-8333-333333333333',
  name: 'Prof. New',
  email: 'new@college.edu',
  role: 'teacher',
  status: 'pending',
  created_at: '2026-07-01T10:00:00Z',
};

export const ADMIN = {
  id: '44444444-4444-4444-8444-444444444444',
  name: 'Admin One',
  email: 'admin@college.edu',
  role: 'admin',
  status: 'active',
};

export const EVENT_ID = '55555555-5555-4555-8555-555555555555';
export const REGISTRATION_ID = '66666666-6666-4666-8666-666666666666';

export const EVENT_LIST_ITEM = {
  id: EVENT_ID,
  title: 'Annual Tech Fest',
  event_type: 'in_college',
  category: 'both',
  status: 'approved',
  start_date: '2026-08-01T00:00:00',
  end_date: '2026-08-03T00:00:00',
  registration_count: 12,
  created_by_name: 'Admin One',
};

// verbatim EventOut: bare object with embedded success, no data wrapper
export const EVENT_DETAIL = {
  success: true,
  id: EVENT_ID,
  title: 'Annual Tech Fest',
  description: 'Three days of talks and workshops.',
  event_type: 'in_college',
  category: 'both',
  status: 'approved',
  venue: 'Main Auditorium',
  start_date: '2026-08-01T00:00:00',
  end_date: '2026-08-03T00:00:00',
  max_registrations: 0,
  created_by: { id: ADMIN.id, name: ADMIN.name, email: ADMIN.email },
  coordinator: { id: TEACHER.id, name: TEACHER.name, email: TEACHER.email },
  created_at: '2026-07-01T09:00:00',
  updated_at: '2026-07-02T09:00:00',
};

// verbatim registration object: carries its own redundant `success` field
export const REGISTRATION_WITH_STUDENT = {
  success: true,
  id: REGISTRATION_ID,
  event_id: EVENT_ID,
  student_id: STUDENT.id,
  role_type: 'participant',
  status: 'pending',
  registered_at: '2026-07-10T12:00:00',
  student: { id: STUDENT.id, name: STUDENT.name, email: STUDENT.email },
};

export const REGISTRATION_WITH_EVENT = {
  success: true,
  id: REGISTRATION_ID,
  event_id: EVENT_ID,
  role_type: 'participant',
  status: 'pending',
  registered_at: '2026-07-10T12:00:00',
  event: {
    id: EVENT_ID,
    title: 'Annual Tech Fest',
    event_type: 'in_college',
    start_date: '2026-08-01T00:00:00',
    end_date: '2026-08-03T00:00:00',
  },
};

export function paginated<T>(items: T[], page = 1, limit = 20) {
  return {
    success: true,
    data: items,
    meta: { page, limit, total: items.length, total_pages: items.length ? 1 : 0 },
  };
}

export function legacyList<T>(key: 'items' | 'users', rows: T[], page = 1, limit = 20) {
  return {
    success: true,
    [key]: rows,
    total: rows.length,
    page,
    limit,
    total_pages: rows.length ? 1 : 0,
  };
}

export const appError = (code: string, message: string) => ({
  success: false,
  error: { code, message },
});
