import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient

from app.api import deps
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException

STUDENT_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()
TEACHER_ID = uuid.uuid4()


class TestAttendanceSchemas:
    def test_attendance_record_valid_present(self):
        from app.schemas.attendance import AttendanceRecord

        rec = AttendanceRecord(studentId=STUDENT_ID, present=True)
        assert rec.studentId == STUDENT_ID
        assert rec.present is True

    def test_attendance_record_valid_absent(self):
        from app.schemas.attendance import AttendanceRecord

        rec = AttendanceRecord(studentId=STUDENT_ID, present=False)
        assert rec.present is False

    def test_bulk_request_valid(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord

        req = BulkAttendanceRequest(
            eventId=EVENT_ID,
            date=date(2026, 7, 4),
            records=[
                AttendanceRecord(studentId=STUDENT_ID, present=True),
            ],
        )
        assert req.eventId == EVENT_ID

    def test_bulk_request_duplicate_students_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord

        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[
                    AttendanceRecord(studentId=STUDENT_ID, present=True),
                    AttendanceRecord(studentId=STUDENT_ID, present=False),
                ],
            )

    def test_bulk_request_empty_records_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest

        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[],
            )

    def test_bulk_request_too_many_records_rejected(self):
        from app.schemas.attendance import BulkAttendanceRequest, AttendanceRecord

        with pytest.raises(ValidationError):
            BulkAttendanceRequest(
                eventId=EVENT_ID,
                date=date(2026, 7, 4),
                records=[AttendanceRecord(studentId=uuid.uuid4(), present=True) for _ in range(101)],
            )

    def test_bulk_response(self):
        from app.schemas.attendance import BulkAttendanceResponse

        resp = BulkAttendanceResponse(count=45, message="Attendance marked for 45 students")
        assert resp.count == 45


class TestAttendanceService:
    @pytest.mark.asyncio
    async def test_mark_bulk_success(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "approved"
        mock_event.start_date = datetime(2026, 7, 4)
        mock_event.end_date = datetime(2026, 7, 5)
        db.get.return_value = mock_event
        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        reg_result = MagicMock()
        reg_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[mock_reg]))
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[reg_result, empty_result])

        records_data = [{"studentId": STUDENT_ID, "present": True}]
        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4), records_data,
            {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert result["count"] == 1
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_bulk_event_not_found(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4), [],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_forbidden_not_coordinator(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4), [],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_admin_bypass(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        mock_event.status = "approved"
        mock_event.start_date = datetime(2026, 7, 4)
        mock_event.end_date = datetime(2026, 7, 5)
        db.get.return_value = mock_event
        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        reg_result = MagicMock()
        reg_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[mock_reg]))
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[reg_result, empty_result])

        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4),
            [{"studentId": STUDENT_ID, "present": True}],
            {"sub": str(uuid.uuid4()), "role": "admin"},
        )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_mark_bulk_event_not_approved(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "draft"
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="approved events"):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4),
                [{"studentId": STUDENT_ID, "present": True}],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_date_outside_event_window(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "approved"
        mock_event.start_date = datetime(2026, 7, 4)
        mock_event.end_date = datetime(2026, 7, 5)
        db.get.return_value = mock_event

        with pytest.raises(ConflictException, match="within the event dates"):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 8, 1),
                [{"studentId": STUDENT_ID, "present": True}],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_student_not_registered(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "approved"
        mock_event.start_date = datetime(2026, 7, 4)
        mock_event.end_date = datetime(2026, 7, 5)
        db.get.return_value = mock_event
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        with pytest.raises(ConflictException, match="not registered"):
            await AttendanceService.mark_bulk(
                db, EVENT_ID, date(2026, 7, 4),
                [{"studentId": STUDENT_ID, "present": True}],
                {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_mark_bulk_upsert_existing_record(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        mock_event.status = "approved"
        mock_event.start_date = datetime(2026, 7, 4)
        mock_event.end_date = datetime(2026, 7, 5)
        db.get.return_value = mock_event

        mock_reg = MagicMock()
        mock_reg.student_id = STUDENT_ID
        db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_reg])))
        )

        result = await AttendanceService.mark_bulk(
            db, EVENT_ID, date(2026, 7, 4),
            [{"studentId": STUDENT_ID, "present": True}],
            {"sub": str(TEACHER_ID), "role": "teacher"},
        )

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_event_attendance_success(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        att = MagicMock()
        att.id = uuid.uuid4()
        att.event_id = EVENT_ID
        att.student_id = STUDENT_ID
        att.attendance_date = date(2026, 7, 4)
        att.status = "present"
        att.marker = MagicMock()
        att.marker.id = TEACHER_ID
        att.marker.name = "Dr. Rajesh"
        att.student = MagicMock()
        att.student.id = STUDENT_ID
        att.student.name = "Priya Singh"
        att.student.email = "priya@college.edu"
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[att]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_event_attendance(
            db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            page=1, limit=20,
        )

        assert total == 1
        records_list = list(records)
        assert len(records_list) == 1

    @pytest.mark.asyncio
    async def test_get_event_attendance_forbidden(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.uuid4()
        db.get.return_value = mock_event

        with pytest.raises(ForbiddenException):
            await AttendanceService.get_event_attendance(
                db, EVENT_ID, {"sub": str(STUDENT_ID), "role": "student"},
            )

    @pytest.mark.asyncio
    async def test_get_student_attendance_success(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        att = MagicMock()
        att.id = uuid.uuid4()
        att.event_id = EVENT_ID
        att.student_id = STUDENT_ID
        att.attendance_date = date(2026, 7, 4)
        att.status = "present"
        att.event = MagicMock()
        att.event.id = EVENT_ID
        att.event.title = "Tech Fest"
        att.event.event_type = "in_college"
        att.event.start_date = "2026-07-04T00:00:00Z"
        att.event.end_date = "2026-07-05T00:00:00Z"
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[att]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_student_attendance(
            db, str(STUDENT_ID), page=1, limit=20,
        )

        assert total == 1

    @pytest.mark.asyncio
    async def test_get_event_attendance_event_not_found(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(NotFoundException, match="Event not found"):
            await AttendanceService.get_event_attendance(
                db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            )

    @pytest.mark.asyncio
    async def test_get_event_attendance_with_date_filter(self):
        from app.services.attendance import AttendanceService
        from datetime import date

        db = AsyncMock()
        mock_event = MagicMock()
        mock_event.coordinator_id = uuid.UUID(str(TEACHER_ID))
        db.get.return_value = mock_event
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        att = MagicMock()
        att.id = uuid.uuid4()
        att.event_id = EVENT_ID
        att.student_id = STUDENT_ID
        att.attendance_date = date(2026, 7, 4)
        att.status = "present"
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[att]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_event_attendance(
            db, EVENT_ID, {"sub": str(TEACHER_ID), "role": "teacher"},
            att_date=date(2026, 7, 4), page=1, limit=20,
        )

        assert total == 1

    @pytest.mark.asyncio
    async def test_get_student_attendance_with_event_filter(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_student_attendance(
            db, str(STUDENT_ID), event_id=EVENT_ID, page=1, limit=20,
        )

        assert total == 0

    @pytest.mark.asyncio
    async def test_get_student_attendance_with_status_filter(self):
        from app.services.attendance import AttendanceService

        db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        db.execute = AsyncMock(side_effect=[count_result, data_result])

        records, total = await AttendanceService.get_student_attendance(
            db, str(STUDENT_ID), status_filter="present", page=1, limit=20,
        )

        assert total == 0


@pytest.fixture
def coordinator_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(TEACHER_ID), "role": "teacher"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


@pytest.fixture
def admin_att_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(uuid.uuid4()), "role": "admin"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


@pytest.fixture
def student_att_app():
    from fastapi import FastAPI
    from app.api.v1.attendance import router
    from app.core.exceptions import register_exception_handlers
    from app.api import deps

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    async def mock_user():
        return {"sub": str(STUDENT_ID), "role": "student"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    return app


class TestAttendanceAPI:
    @pytest.mark.asyncio
    async def test_bulk_attendance_200(self, coordinator_app):
        with patch("app.services.attendance.AttendanceService.mark_bulk", return_value={"count": 1, "message": "ok"}):
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/attendance/bulk",
                    json={
                        "eventId": str(EVENT_ID),
                        "date": "2026-07-04",
                        "records": [{"studentId": str(STUDENT_ID), "present": True}],
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["count"] == 1

    @pytest.mark.asyncio
    async def test_bulk_attendance_validation_error(self, coordinator_app):
        transport = ASGITransport(app=coordinator_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/attendance/bulk",
                json={"eventId": str(EVENT_ID), "date": "2026-07-04", "records": []},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_attendance_forbidden(self, student_att_app):
        transport = ASGITransport(app=student_att_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/attendance/bulk",
                json={
                    "eventId": str(EVENT_ID),
                    "date": "2026-07-04",
                    "records": [{"studentId": str(STUDENT_ID), "present": True}],
                },
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_attendance_not_found(self, coordinator_app):
        with patch("app.services.attendance.AttendanceService.mark_bulk") as mock_mark:
            mock_mark.side_effect = NotFoundException("Event not found")
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/attendance/bulk",
                    json={
                        "eventId": str(EVENT_ID),
                        "date": "2026-07-04",
                        "records": [{"studentId": str(STUDENT_ID), "present": True}],
                    },
                )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_event_attendance_200(self, coordinator_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.attendance_date = "2026-07-04"
        mock_att.status = "present"
        mock_att.student = MagicMock()
        mock_att.student.id = STUDENT_ID
        mock_att.student.name = "Priya"
        mock_att.student.email = "priya@college.edu"
        mock_att.marker = MagicMock()
        mock_att.marker.id = TEACHER_ID
        mock_att.marker.name = "Dr. Rajesh"

        with patch("app.services.attendance.AttendanceService.get_event_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=coordinator_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/attendance/event/{EVENT_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_my_attendance_200(self, student_att_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.attendance_date = "2026-07-04"
        mock_att.status = "present"
        mock_att.event = MagicMock()
        mock_att.event.id = EVENT_ID
        mock_att.event.title = "Tech Fest"
        mock_att.event.event_type = "in_college"
        mock_att.event.start_date = "2026-07-04T00:00:00Z"
        mock_att.event.end_date = "2026-07-05T00:00:00Z"

        with patch("app.services.attendance.AttendanceService.get_student_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=student_att_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/attendance/my")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_student_attendance_as_admin(self, admin_att_app):
        mock_att = MagicMock()
        mock_att.id = uuid.uuid4()
        mock_att.event_id = EVENT_ID
        mock_att.student_id = STUDENT_ID
        mock_att.attendance_date = "2026-07-04"
        mock_att.status = "present"
        mock_att.event = MagicMock()
        mock_att.event.id = EVENT_ID
        mock_att.event.title = "Tech Fest"
        mock_att.event.event_type = "in_college"
        mock_att.event.start_date = "2026-07-04T00:00:00Z"
        mock_att.event.end_date = "2026-07-05T00:00:00Z"

        with patch("app.services.attendance.AttendanceService.get_student_attendance", return_value=([mock_att], 1)):
            transport = ASGITransport(app=admin_att_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/api/v1/attendance/student/{STUDENT_ID}")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_student_cannot_access_event_attendance(self, student_att_app):
        transport = ASGITransport(app=student_att_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/attendance/event/{EVENT_ID}")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthorized_access_to_attendance(self):
        from fastapi import FastAPI
        from app.api.v1.attendance import router
        from app.core.exceptions import register_exception_handlers

        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/attendance/my")
            assert resp.status_code == 401
