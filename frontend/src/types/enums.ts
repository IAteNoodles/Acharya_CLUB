export type Role = 'student' | 'teacher' | 'admin';
export type UserStatus = 'pending' | 'active' | 'rejected';
export type EventType = 'in_college' | 'out_college';
export type EventCategory = 'volunteer' | 'participant' | 'both';
export type EventStatus = 'draft' | 'pending' | 'approved' | 'rejected';
export type RegistrationRole = 'volunteer' | 'participant';
export type RegistrationStatus = 'pending' | 'accepted' | 'rejected';
export type AttendanceStatus = 'present' | 'absent' | 'late';
export type NotificationType =
  | 'registration_accepted'
  | 'registration_rejected'
  | 'event_approved'
  | 'event_rejected'
  | 'teacher_approved'
  | 'teacher_rejected';
