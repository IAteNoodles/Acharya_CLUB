import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { markBulkAttendance } from '@/api/attendance.api';
import * as eventsApi from '@/api/events.api';
import * as registrationsApi from '@/api/registrations.api';
import { tokens } from '@/api/tokens';
import { ADMIN, appError, BASE, STUDENT, TEACHER } from './msw/fixtures';
import { server } from './msw/server';

interface StoredEvent {
  id: string;
  title: string;
  description: string | null;
  event_type: string;
  category: string;
  status: string;
  venue: string | null;
  start_date: string;
  end_date: string;
  max_registrations: number;
  created_by: typeof ADMIN | null;
  coordinator: typeof TEACHER | null;
  created_at: string;
  updated_at: string;
}

interface StoredRegistration {
  id: string;
  event_id: string;
  student_id: string;
  role_type: string;
  status: string;
  registered_at: string;
}

function installStatefulBackend() {
  const events = new Map<string, StoredEvent>();
  const registrations = new Map<string, StoredRegistration>();
  const attendance: { event_id: string; student_id: string; date: string; status: string }[] = [];
  let sequence = 0;
  const nextId = () => `00000000-0000-4000-8000-${String(++sequence).padStart(12, '0')}`;

  server.use(
    http.post(`${BASE}/events`, async ({ request }) => {
      const body = (await request.json()) as Record<string, string>;
      const event: StoredEvent = {
        id: nextId(),
        title: body.title,
        description: body.description ?? null,
        event_type: body.event_type,
        category: body.category,
        status: body.event_type === 'in_college' ? 'draft' : 'pending',
        venue: body.venue,
        start_date: body.start_date,
        end_date: body.end_date,
        max_registrations: 0,
        created_by: body.event_type === 'in_college' ? ADMIN : null,
        coordinator: null,
        created_at: '2026-07-13T00:00:00',
        updated_at: '2026-07-13T00:00:00',
      };
      events.set(event.id, event);
      return HttpResponse.json({ success: true, ...event }, { status: 201 });
    }),
    http.get(`${BASE}/events/:id`, ({ params }) => {
      const event = events.get(params.id as string);
      if (!event) return HttpResponse.json(appError('NOT_FOUND', 'Event not found'), { status: 404 });
      return HttpResponse.json({ success: true, ...event });
    }),
    http.patch(`${BASE}/events/:id/assign-coordinator`, ({ params }) => {
      const event = events.get(params.id as string)!;
      event.coordinator = TEACHER;
      return HttpResponse.json({ success: true, ...event });
    }),
    http.patch(`${BASE}/events/:id/approve`, ({ params }) => {
      const event = events.get(params.id as string)!;
      if (event.status === 'approved') {
        return HttpResponse.json(appError('CONFLICT', 'Event already approved'), { status: 409 });
      }
      event.status = 'approved';
      return HttpResponse.json({ success: true, ...event });
    }),
    http.post(`${BASE}/registrations`, async ({ request }) => {
      const body = (await request.json()) as { event_id: string; role_type: string };
      const event = events.get(body.event_id);
      if (!event || event.status !== 'approved' || !event.coordinator) {
        return HttpResponse.json(appError('CONFLICT', 'Event has no coordinator assigned'), {
          status: 409,
        });
      }
      const duplicate = [...registrations.values()].some(
        (reg) => reg.event_id === body.event_id && reg.role_type === body.role_type,
      );
      if (duplicate) {
        return HttpResponse.json(appError('CONFLICT', 'Already registered for this event'), {
          status: 409,
        });
      }
      const registration: StoredRegistration = {
        id: nextId(),
        event_id: body.event_id,
        student_id: STUDENT.id,
        role_type: body.role_type,
        status: 'pending',
        registered_at: '2026-07-13T01:00:00',
      };
      registrations.set(registration.id, registration);
      return HttpResponse.json(
        { success: true, data: { success: true, ...registration } },
        { status: 201 },
      );
    }),
    http.patch(`${BASE}/registrations/:id/accept`, ({ params }) => {
      const registration = registrations.get(params.id as string)!;
      if (registration.status !== 'pending') {
        return HttpResponse.json(appError('CONFLICT', 'Registration is not pending'), {
          status: 409,
        });
      }
      registration.status = 'accepted';
      return HttpResponse.json({ success: true, data: { success: true, ...registration } });
    }),
    http.post(`${BASE}/attendance/bulk`, async ({ request }) => {
      const body = (await request.json()) as {
        eventId: string;
        date: string;
        records: { studentId: string; present: boolean }[];
      };
      for (const record of body.records) {
        const hasAccepted = [...registrations.values()].some(
          (reg) =>
            reg.event_id === body.eventId &&
            reg.student_id === record.studentId &&
            reg.status === 'accepted',
        );
        if (!hasAccepted) {
          return HttpResponse.json(
            appError('CONFLICT', 'Student does not hold an accepted registration'),
            { status: 409 },
          );
        }
        attendance.push({
          event_id: body.eventId,
          student_id: record.studentId,
          date: body.date,
          status: record.present ? 'present' : 'absent',
        });
      }
      return HttpResponse.json({
        success: true,
        data: {
          success: true,
          count: body.records.length,
          message: `Attendance marked for ${body.records.length} student(s)`,
        },
      });
    }),
    http.get(`${BASE}/attendance/my`, () =>
      HttpResponse.json({
        success: true,
        data: attendance.map((record, index) => ({
          success: true,
          id: `record-${index}`,
          ...record,
        })),
        meta: { page: 1, limit: 20, total: attendance.length, total_pages: 1 },
      }),
    ),
  );

  return { events, registrations, attendance };
}

describe('lifecycle A: in-college event from creation to attendance', () => {
  beforeEach(() => {
    tokens.setAccess('access-valid');
  });

  it('runs create → assign → approve → join → accept → attendance end-to-end', async () => {
    const state = installStatefulBackend();

    const draft = await eventsApi.createEvent({
      title: 'Sports Day',
      description: null,
      event_type: 'in_college',
      category: 'both',
      venue: 'Grounds',
      start_date: '2026-09-01',
      end_date: '2026-09-02',
    });
    expect(draft.status).toBe('draft');

    // registration before approval/coordinator is refused with a 409 business message
    await expect(registrationsApi.register(draft.id, 'participant')).rejects.toMatchObject({
      status: 409,
      message: 'Event has no coordinator assigned',
    });

    const withCoordinator = await eventsApi.assignCoordinator(draft.id, TEACHER.id);
    expect(withCoordinator.coordinator?.id).toBe(TEACHER.id);

    const approved = await eventsApi.approveEvent(draft.id);
    expect(approved.status).toBe('approved');

    // approving twice is a 409
    await expect(eventsApi.approveEvent(draft.id)).rejects.toMatchObject({ status: 409 });

    const registration = await registrationsApi.register(draft.id, 'participant');
    expect(registration.status).toBe('pending');

    // duplicate registration for the same role is refused
    await expect(registrationsApi.register(draft.id, 'participant')).rejects.toMatchObject({
      status: 409,
    });

    const accepted = await registrationsApi.acceptRegistration(registration.id);
    expect(accepted.status).toBe('accepted');

    const result = await markBulkAttendance(draft.id, '2026-09-02', [
      { studentId: STUDENT.id, present: true },
    ]);
    expect(result.count).toBe(1);

    const myAttendance = await (await import('@/api/attendance.api')).listMyAttendance();
    expect(myAttendance.items).toHaveLength(1);
    expect(myAttendance.items[0].status).toBe('present');
    expect(state.attendance).toHaveLength(1);
  });

  it('lifecycle B: student-raised out-college event lands pending', async () => {
    installStatefulBackend();

    const submitted = await eventsApi.createEvent({
      title: 'Inter-College Hackathon',
      description: 'Brochure: https://example.com/brochure.pdf',
      event_type: 'out_college',
      category: 'participant',
      venue: 'IIT Campus',
      start_date: '2026-10-01',
      end_date: '2026-10-02',
    });
    expect(submitted.status).toBe('pending');

    const fetched = await eventsApi.getEvent(submitted.id);
    expect(fetched.title).toBe('Inter-College Hackathon');
    expect(fetched.status).toBe('pending');

    const approved = await eventsApi.approveEvent(submitted.id);
    expect(approved.status).toBe('approved');
  });
});
