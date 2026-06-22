import pytest
from pydantic import ValidationError


class TestUserSchemas:
    def test_pending_teachers_response(self):
        from app.schemas.users import PendingTeachersResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="pending",
        )
        resp = PendingTeachersResponse(
            users=[user],
            total=1,
            page=1,
            limit=20,
            total_pages=1,
        )
        assert resp.success is True
        assert len(resp.users) == 1
        assert resp.users[0].status == "pending"
        assert resp.total_pages == 1

    def test_pending_teachers_response_empty(self):
        from app.schemas.users import PendingTeachersResponse

        resp = PendingTeachersResponse(users=[], total=0, page=1, limit=20, total_pages=0)
        assert resp.users == []
        assert resp.total == 0

    def test_teacher_list_response_with_search(self):
        from app.schemas.users import TeacherListResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440001",
            name="Dr. Rajesh Kumar",
            email="rajesh@college.edu",
            role="teacher",
            status="active",
        )
        resp = TeacherListResponse(users=[user], total=1, page=1, limit=20, total_pages=1)
        assert resp.success is True
        assert resp.users[0].name == "Dr. Rajesh Kumar"

    def test_user_action_response(self):
        from app.schemas.users import UserActionResponse, UserOut

        user = UserOut(
            id="550e8400-e29b-41d4-a716-446655440002",
            name="Teacher B",
            email="b@college.edu",
            role="teacher",
            status="active",
        )
        resp = UserActionResponse(data=user)
        assert resp.success is True
        assert resp.data.status == "active"

    def test_user_out_rejects_invalid_uuid(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="not-a-uuid",
                name="Bad",
                email="bad@test.com",
                role="teacher",
                status="pending",
            )

    def test_user_out_rejects_invalid_role(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="550e8400-e29b-41d4-a716-446655440003",
                name="Bad",
                email="bad@test.com",
                role="superadmin",
                status="pending",
            )

    def test_user_out_rejects_invalid_status(self):
        from app.schemas.users import UserOut

        with pytest.raises(ValidationError):
            UserOut(
                id="550e8400-e29b-41d4-a716-446655440004",
                name="Bad",
                email="bad@test.com",
                role="teacher",
                status="nonexistent",
            )


def _make_mock_user(**kwargs):
    from unittest.mock import MagicMock
    u = MagicMock()
    for k, v in kwargs.items():
        setattr(u, k, v)
    return u


def _make_user_out(**kwargs):
    from app.schemas.users import UserOut
    return UserOut(id="550e8400-e29b-41d4-a716-446655440099", name="Placeholder",
                   email="p@college.edu", role="teacher", status="active"
                   ).model_copy(update=kwargs)


class TestUserService:
    @pytest.mark.asyncio
    async def test_get_pending_teachers_returns_paginated(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.schemas.users import UserOut
        from app.services.user import get_pending_teachers

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_mock_user(
                id="550e8400-e29b-41d4-a716-446655440010",
                name="Teacher A",
                email="a@college.edu",
                role="teacher",
                status="pending",
                created_at=None,
                updated_at=None,
            ),
        ]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        result = await get_pending_teachers(mock_session, page=1, limit=20)

        assert result.total == 1
        assert len(result.users) == 1

    @pytest.mark.asyncio
    async def test_get_pending_teachers_computes_offset(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import get_pending_teachers

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        await get_pending_teachers(mock_session, page=2, limit=10)

        call_args = mock_session.execute.call_args_list
        first_stmt = call_args[0][0][0]
        assert "OFFSET" in str(first_stmt).upper()

    @pytest.mark.asyncio
    async def test_approve_teacher_success(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import approve_teacher

        mock_session = AsyncMock()
        mock_user = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440011",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="pending",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_result.scalar_one.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await approve_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440011")

        assert result.status == "active"
        assert mock_session.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_approve_teacher_not_found(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import approve_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "nonexistent")
        assert "not found" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_approve_teacher_not_a_teacher(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import approve_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440012",
            name="Student A",
            email="s@college.edu",
            role="student",
            status="pending",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440012")
        assert "not found" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_approve_teacher_already_active(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import approve_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440013",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="active",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440013")
        assert "already active" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_approve_teacher_already_rejected(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import approve_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440014",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="rejected",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await approve_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440014")
        assert "already rejected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_reject_teacher_success(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import reject_teacher

        mock_session = AsyncMock()
        mock_user = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440015",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="pending",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_result.scalar_one.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await reject_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440015")

        assert result.status == "rejected"
        assert mock_session.commit.await_count == 2

    @pytest.mark.asyncio
    async def test_reject_teacher_not_found(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import reject_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await reject_teacher(mock_session, "nonexistent")
        assert "not found" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_reject_teacher_already_rejected(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import reject_teacher

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_mock_user(
            id="550e8400-e29b-41d4-a716-446655440016",
            name="Teacher A",
            email="a@college.edu",
            role="teacher",
            status="rejected",
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc:
            await reject_teacher(mock_session, "550e8400-e29b-41d4-a716-446655440016")
        assert "already rejected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_get_active_teachers_paginated(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import get_active_teachers

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_mock_user(
                id="550e8400-e29b-41d4-a716-446655440017",
                name="Dr. Rajesh Kumar",
                email="rajesh@college.edu",
                role="teacher",
                status="active",
                created_at=None,
                updated_at=None,
            ),
        ]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        result = await get_active_teachers(mock_session, page=1, limit=20)

        assert len(result.users) == 1
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_active_teachers_with_search(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.services.user import get_active_teachers

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        await get_active_teachers(mock_session, page=1, limit=20, search="rajesh")

        call_args = mock_session.execute.call_args_list
        first_stmt = str(call_args[0][0][0]).upper()
        assert "LIKE" in first_stmt


class TestUsersAPI:
    @pytest.fixture
    def api_app(self):
        from fastapi import FastAPI
        from app.api.v1.users import router
        from app.api import deps

        app = FastAPI()
        app.include_router(router)

        async def mock_admin():
            return {"sub": "admin-uuid", "role": "admin"}

        async def mock_current():
            return {"sub": "admin-uuid", "role": "admin"}

        app.dependency_overrides[deps.get_current_user] = mock_current
        app.dependency_overrides[deps.require_admin] = mock_admin
        return app

    @pytest.mark.asyncio
    async def test_get_pending_teachers_returns_200(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import PendingTeachersResponse

        with patch("app.services.user.get_pending_teachers") as mock_service:
            mock_service.return_value = PendingTeachersResponse(
                users=[_make_user_out(status="pending")],
                total=1, page=1, limit=20, total_pages=1,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/pending-teachers")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert len(data["users"]) == 1
            assert data["users"][0]["status"] == "pending"
            assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_pending_teachers_empty(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import PendingTeachersResponse

        with patch("app.services.user.get_pending_teachers") as mock_service:
            mock_service.return_value = PendingTeachersResponse(
                users=[], total=0, page=1, limit=20, total_pages=0,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/pending-teachers")

            assert resp.status_code == 200
            data = resp.json()
            assert data["users"] == []
            assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_pending_teachers_respects_pagination(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import PendingTeachersResponse

        with patch("app.services.user.get_pending_teachers") as mock_service:
            mock_service.return_value = PendingTeachersResponse(
                users=[], total=0, page=2, limit=10, total_pages=0,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/pending-teachers?page=2&limit=10")

            assert resp.status_code == 200
            assert resp.json()["page"] == 2
            assert mock_service.call_args[1]["page"] == 2
            assert mock_service.call_args[1]["limit"] == 10

    @pytest.mark.asyncio
    async def test_approve_teacher_200(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient

        with patch("app.services.user.approve_teacher") as mock_service:
            mock_service.return_value = _make_user_out(status="active")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/uuid-1/approve")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_approve_teacher_404(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from fastapi import HTTPException

        with patch("app.services.user.approve_teacher") as mock_service:
            mock_service.side_effect = HTTPException(status_code=404, detail="User not found")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/nonexistent/approve")

            assert resp.status_code == 404
            assert resp.json()["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_approve_teacher_409_active(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from fastapi import HTTPException

        with patch("app.services.user.approve_teacher") as mock_service:
            mock_service.side_effect = HTTPException(status_code=409, detail="User is already active")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/uuid-1/approve")

            assert resp.status_code == 409
            assert resp.json()["detail"] == "User is already active"

    @pytest.mark.asyncio
    async def test_reject_teacher_200(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient

        with patch("app.services.user.reject_teacher") as mock_service:
            mock_service.return_value = _make_user_out(status="rejected")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/uuid-1/reject")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_teacher_404(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from fastapi import HTTPException

        with patch("app.services.user.reject_teacher") as mock_service:
            mock_service.side_effect = HTTPException(status_code=404, detail="User not found")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/nonexistent/reject")

            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_teacher_409(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from fastapi import HTTPException

        with patch("app.services.user.reject_teacher") as mock_service:
            mock_service.side_effect = HTTPException(status_code=409, detail="User is already rejected")

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch("/api/v1/users/uuid-1/reject")

            assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_teachers_200(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import TeacherListResponse

        with patch("app.services.user.get_active_teachers") as mock_service:
            mock_service.return_value = TeacherListResponse(
                users=[_make_user_out(name="Dr. Rajesh Kumar")],
                total=1, page=1, limit=20, total_pages=1,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/teachers")

            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert len(data["users"]) == 1

    @pytest.mark.asyncio
    async def test_get_teachers_with_search(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import TeacherListResponse

        with patch("app.services.user.get_active_teachers") as mock_service:
            mock_service.return_value = TeacherListResponse(
                users=[], total=0, page=1, limit=20, total_pages=0,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/teachers?search=rajesh")

            assert resp.status_code == 200
            assert mock_service.call_args[1]["search"] == "rajesh"

    @pytest.mark.asyncio
    async def test_get_teachers_empty(self, api_app):
        from unittest.mock import patch
        from httpx import ASGITransport, AsyncClient
        from app.schemas.users import TeacherListResponse

        with patch("app.services.user.get_active_teachers") as mock_service:
            mock_service.return_value = TeacherListResponse(
                users=[], total=0, page=1, limit=20, total_pages=0,
            )

            transport = ASGITransport(app=api_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/users/teachers")

            assert resp.status_code == 200
            assert resp.json()["users"] == []

    @pytest.mark.asyncio
    async def test_users_endpoints_require_auth(self):
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from app.api.v1.users import router

        app = FastAPI()
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/users/pending-teachers")
            assert resp.status_code == 401

            resp = await client.get("/api/v1/users/teachers")
            assert resp.status_code == 401

            resp = await client.patch("/api/v1/users/some-id/approve")
            assert resp.status_code == 401

            resp = await client.patch("/api/v1/users/some-id/reject")
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_users_endpoints_require_admin(self):
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from app.api.v1.users import router
        from app.api import deps

        app = FastAPI()
        app.include_router(router)

        async def mock_student():
            return {"sub": "student-uuid", "role": "student"}

        app.dependency_overrides[deps.get_current_user] = mock_student
        app.dependency_overrides[deps.require_admin] = deps.require_admin

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/users/pending-teachers")
            assert resp.status_code == 403
