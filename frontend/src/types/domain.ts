import type {
  AttendanceStatus,
  EventCategory,
  EventStatus,
  EventType,
  NotificationType,
  RegistrationRole,
  RegistrationStatus,
  Role,
  UserStatus,
} from './enums';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: UserStatus;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserBrief {
  id: string;
  name: string;
  email: string;
}

export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_type: EventType;
  category: EventCategory;
  status: EventStatus;
  venue: string | null;
  start_date: string;
  end_date: string;
  max_registrations: number;
  created_by: UserBrief | null;
  coordinator: UserBrief | null;
  created_at: string;
  updated_at: string;
}

export interface EventListItem {
  id: string;
  title: string;
  event_type: EventType;
  category: EventCategory;
  status: EventStatus;
  start_date: string;
  end_date: string;
  registration_count: number;
  created_by_name: string | null;
}

export interface RegistrationEventBrief {
  id: string;
  title: string;
  event_type: EventType;
  start_date: string;
  end_date: string;
}

export interface Registration {
  id: string;
  event_id: string;
  student_id?: string;
  role_type: RegistrationRole;
  status: RegistrationStatus;
  registered_at: string;
  event?: RegistrationEventBrief;
  student?: UserBrief;
}

export interface AttendanceRecord {
  id: string;
  event_id: string;
  student_id: string;
  date: string;
  status: AttendanceStatus;
  student?: UserBrief | null;
  marked_by?: { id: string; name: string } | null;
  event?: RegistrationEventBrief | null;
}

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  related_entity_type: 'event' | 'registration' | 'user' | null;
  related_entity_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface DashboardStats {
  users: {
    total: number;
    by_role: Record<string, number>;
    by_status: Record<string, number>;
    by_role_status: Record<string, Record<string, number>>;
  };
  events: { total: number; by_status: Record<string, number>; by_type: Record<string, number> };
  registrations: { total: number; by_status: Record<string, number> };
  attendance: { total: number; by_status: Record<string, number> };
  notifications: { total: number; unread: number };
}

export interface Paginated<T> {
  items: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}
