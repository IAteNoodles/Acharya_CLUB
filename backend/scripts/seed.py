import asyncio
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.database import engine
from app.models.user import User, Role, UserStatus
from app.models.event import Event, EventType, EventCategory, EventStatus
from app.models.registration import Registration, RegistrationRole, RegistrationStatus
from app.models.attendance import Attendance, AttendanceStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # ── Cleanup existing data (reverse dependency order) ─
        await session.execute(Attendance.__table__.delete())
        await session.execute(Registration.__table__.delete())
        await session.execute(Event.__table__.delete())
        await session.execute(User.__table__.delete())

        admin_password = pwd_context.hash("Admin@123")
        teacher_password = pwd_context.hash("Teacher@123")
        student_password = pwd_context.hash("Student@123")

        # ── Admin ──────────────────────────────────────────
        admin = User(
            name="System Administrator",
            email="admin@college.edu",
            password_hash=admin_password,
            role=Role.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)
        await session.flush()
        print(f"  Admin created: {admin.email}")

        # ── Teachers ───────────────────────────────────────
        active_teacher = User(
            name="Dr. Rajesh Kumar",
            email="rajesh.kumar@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.ACTIVE,
        )
        session.add(active_teacher)

        pending_teacher = User(
            name="Prof. Sunita Sharma",
            email="sunita.sharma@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.PENDING,
        )
        session.add(pending_teacher)

        rejected_teacher = User(
            name="Dr. Amit Patel",
            email="amit.patel@college.edu",
            password_hash=teacher_password,
            role=Role.TEACHER,
            status=UserStatus.REJECTED,
        )
        session.add(rejected_teacher)

        await session.flush()
        print("  Teachers created: 1 active, 1 pending, 1 rejected")

        # ── Students ───────────────────────────────────────
        student1 = User(
            name="Priya Singh",
            email="priya.singh@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student1)

        student2 = User(
            name="Arjun Nair",
            email="arjun.nair@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student2)

        student3 = User(
            name="Neha Gupta",
            email="neha.gupta@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        session.add(student3)

        pending_student = User(
            name="Rohan Desai",
            email="rohan.desai@college.edu",
            password_hash=student_password,
            role=Role.STUDENT,
            status=UserStatus.PENDING,
        )
        session.add(pending_student)

        await session.flush()
        print("  Students created: 3 active, 1 pending")

        now = datetime.now(timezone.utc)

        # ── Events ─────────────────────────────────────────
        future_start = now + timedelta(days=14)
        future_end = future_start + timedelta(days=1)
        past_start = now - timedelta(days=7)
        past_end = past_start
        next_week_start = now + timedelta(days=7)
        next_week_end = now + timedelta(days=8)

        event1 = Event(
            title="Annual Tech Fest 2026",
            description="A two-day technology festival featuring coding competitions, robotics workshops, and guest lectures.",
            event_type=EventType.IN_COLLEGE,
            category=EventCategory.BOTH,
            status=EventStatus.APPROVED,
            venue="Main Auditorium & CS Block",
            start_date=future_start,
            end_date=future_end,
            max_registrations=200,
            created_by=admin.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event1)

        event2 = Event(
            title="Debate Competition: Current Affairs",
            description="Inter-department debate competition on current affairs topics.",
            event_type=EventType.IN_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.APPROVED,
            venue="Seminar Hall, 3rd Floor",
            start_date=next_week_start,
            end_date=next_week_end,
            max_registrations=32,
            created_by=active_teacher.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event2)

        event3 = Event(
            title="National Hackathon: CodeForCause",
            description="Inter-college national hackathon hosted at our campus.",
            event_type=EventType.OUT_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.PENDING,
            venue="Whole Campus",
            start_date=now + timedelta(days=44),
            end_date=now + timedelta(days=46),
            max_registrations=500,
            created_by=active_teacher.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event3)

        event4 = Event(
            title="Freshers Welcome 2026",
            description="Welcome ceremony for the batch of 2026.",
            event_type=EventType.IN_COLLEGE,
            category=EventCategory.PARTICIPANT,
            status=EventStatus.APPROVED,
            venue="College Ground",
            start_date=past_start,
            end_date=past_end,
            max_registrations=500,
            created_by=admin.id,
            coordinator_id=active_teacher.id,
        )
        session.add(event4)

        await session.flush()
        print("  Events created: 2 approved (in-college), 1 pending (out-college), 1 past")

        # ── Registrations ──────────────────────────────────
        regs = [
            Registration(event_id=event1.id, student_id=student1.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.ACCEPTED),
            Registration(event_id=event1.id, student_id=student1.id, role_type=RegistrationRole.VOLUNTEER, status=RegistrationStatus.ACCEPTED),
            Registration(event_id=event1.id, student_id=student2.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.PENDING),
            Registration(event_id=event2.id, student_id=student3.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.ACCEPTED),
            Registration(event_id=event3.id, student_id=student1.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.PENDING),
            Registration(event_id=event4.id, student_id=student2.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.ACCEPTED),
            Registration(event_id=event4.id, student_id=student3.id, role_type=RegistrationRole.PARTICIPANT, status=RegistrationStatus.ACCEPTED),
        ]
        for r in regs:
            session.add(r)
        await session.flush()
        print("  Registrations created: 7 entries")

        # ── Attendance ─────────────────────────────────────
        att1 = Attendance(
            event_id=event4.id,
            student_id=student2.id,
            marked_by=active_teacher.id,
            attendance_date=past_start.date(),
            status=AttendanceStatus.PRESENT,
        )
        session.add(att1)

        att2 = Attendance(
            event_id=event4.id,
            student_id=student3.id,
            marked_by=active_teacher.id,
            attendance_date=past_start.date(),
            status=AttendanceStatus.ABSENT,
        )
        session.add(att2)

        await session.flush()
        print("  Attendance records created: 2 entries")

        await session.commit()

    await engine.dispose()
    print("\nSeed completed successfully!")
    print("  Admin:     admin@college.edu / Admin@123")
    print("  Teacher:   rajesh.kumar@college.edu / Teacher@123")
    print("  Student:   priya.singh@college.edu / Student@123")


if __name__ == "__main__":
    asyncio.run(seed())
