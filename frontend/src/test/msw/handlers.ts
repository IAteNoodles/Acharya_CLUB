import { http, HttpResponse } from 'msw';
import {
  ADMIN,
  appError,
  BASE,
  EVENT_DETAIL,
  EVENT_LIST_ITEM,
  legacyList,
  paginated,
  PENDING_TEACHER,
  REGISTRATION_WITH_EVENT,
  REGISTRATION_WITH_STUDENT,
  STUDENT,
  TEACHER,
} from './fixtures';

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email === 'pending@college.edu') {
      return HttpResponse.json(appError('HTTP_ERROR', 'Account is not active'), { status: 403 });
    }
    if (body.password !== 'Correct@123') {
      return HttpResponse.json(appError('HTTP_ERROR', 'Invalid email or password'), {
        status: 401,
      });
    }
    const user = body.email === ADMIN.email ? ADMIN : body.email === TEACHER.email ? TEACHER : STUDENT;
    return HttpResponse.json({
      success: true,
      data: { user, accessToken: 'access-1', refreshToken: 'refresh-1' },
    });
  }),

  http.post(`${BASE}/auth/signup`, async ({ request }) => {
    const body = (await request.json()) as { name: string; email: string; role: string };
    if (body.email === 'taken@college.edu') {
      return HttpResponse.json(appError('CONFLICT', 'Email already registered'), { status: 409 });
    }
    const user = {
      id: STUDENT.id,
      name: body.name,
      email: body.email,
      role: body.role,
      status: body.role === 'teacher' ? 'pending' : 'active',
    };
    return HttpResponse.json(
      { success: true, data: { user, accessToken: 'access-1', refreshToken: 'refresh-1' } },
      { status: 201 },
    );
  }),

  http.post(`${BASE}/auth/refresh`, () =>
    HttpResponse.json({
      success: true,
      data: { accessToken: 'access-2', refreshToken: 'refresh-2' },
    }),
  ),

  http.post(`${BASE}/auth/logout`, () =>
    HttpResponse.json({ success: true, data: { message: 'Logged out successfully' } }),
  ),

  http.get(`${BASE}/auth/me`, () =>
    HttpResponse.json({ success: true, data: { user: STUDENT } }),
  ),

  http.get(`${BASE}/events`, () => HttpResponse.json(legacyList('items', [EVENT_LIST_ITEM]))),
  http.get(`${BASE}/events/:id`, () => HttpResponse.json(EVENT_DETAIL)),

  http.post(`${BASE}/registrations`, () =>
    HttpResponse.json({ success: true, data: REGISTRATION_WITH_EVENT }, { status: 201 }),
  ),
  http.get(`${BASE}/registrations/my`, () =>
    HttpResponse.json(paginated([REGISTRATION_WITH_EVENT])),
  ),
  http.get(`${BASE}/registrations/event/:eventId`, () =>
    HttpResponse.json(paginated([REGISTRATION_WITH_STUDENT])),
  ),
  http.patch(`${BASE}/registrations/:id/accept`, () =>
    HttpResponse.json({ success: true, data: { ...REGISTRATION_WITH_STUDENT, status: 'accepted' } }),
  ),
  http.patch(`${BASE}/registrations/:id/reject`, () =>
    HttpResponse.json({ success: true, data: { ...REGISTRATION_WITH_STUDENT, status: 'rejected' } }),
  ),

  http.get(`${BASE}/attendance/event/:eventId`, () => HttpResponse.json(paginated([]))),
  http.get(`${BASE}/attendance/my`, () => HttpResponse.json(paginated([]))),
  http.post(`${BASE}/attendance/bulk`, () =>
    HttpResponse.json({
      success: true,
      data: { success: true, count: 1, message: 'Attendance marked for 1 student(s)' },
    }),
  ),

  http.get(`${BASE}/users/pending-teachers`, () =>
    HttpResponse.json(legacyList('users', [PENDING_TEACHER])),
  ),
  http.get(`${BASE}/users/teachers`, () => HttpResponse.json(legacyList('users', [TEACHER]))),
  http.patch(`${BASE}/users/:id/approve`, () =>
    HttpResponse.json({ success: true, data: { ...PENDING_TEACHER, status: 'active' } }),
  ),
  http.patch(`${BASE}/users/:id/reject`, () =>
    HttpResponse.json({ success: true, data: { ...PENDING_TEACHER, status: 'rejected' } }),
  ),

  http.get(`${BASE}/notifications`, () => HttpResponse.json(paginated([]))),
  http.get(`${BASE}/notifications/unread-count`, () =>
    HttpResponse.json({ success: true, data: { count: 0 } }),
  ),
  http.patch(`${BASE}/notifications/read-all`, () =>
    HttpResponse.json({ success: true, data: { count: 0 } }),
  ),

  http.get(`${BASE}/reports/dashboard`, () =>
    HttpResponse.json({
      success: true,
      data: {
        users: {
          total: 5,
          by_role: { student: 3, teacher: 1, admin: 1 },
          by_status: { active: 4, pending: 1 },
          by_role_status: {
            student: { active: 2, pending: 1 },
            teacher: { active: 1 },
            admin: { active: 1 },
          },
        },
        events: { total: 2, by_status: { approved: 1, pending: 1 }, by_type: { in_college: 1, out_college: 1 } },
        registrations: { total: 4, by_status: { pending: 2, accepted: 2 } },
        attendance: { total: 6, by_status: { present: 5, absent: 1 } },
        notifications: { total: 3, unread: 1 },
      },
    }),
  ),
];
