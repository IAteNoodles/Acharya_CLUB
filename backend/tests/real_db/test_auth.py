import pytest
from sqlalchemy import select

from app.models.user import User
from app.schemas.auth import SignupRequest

pytestmark = [pytest.mark.asyncio, pytest.mark.real_db]


class TestSignupRealDB:
    async def test_creates_student(self, db_session):
        from app.services.auth import signup

        result = await signup(
            db=db_session,
            data=SignupRequest(
                name="Priya Singh",
                email="priya.singh@college.edu",
                password="SecurePass123",
                role="student",
            ),
        )

        assert result["user"]["name"] == "Priya Singh"
        assert result["user"]["email"] == "priya.singh@college.edu"
        assert result["user"]["role"] == "student"
        assert result["user"]["status"] == "active"
        assert "password_hash" not in result["user"]
        assert result["accessToken"] is not None
        assert result["refreshToken"] is not None

        row = await db_session.execute(
            select(User).where(User.email == "priya.singh@college.edu")
        )
        user = row.scalar_one()
        assert user.name == "Priya Singh"
        assert user.role.value == "student"
        assert user.status.value == "active"

    async def test_creates_teacher_pending(self, db_session):
        from app.services.auth import signup

        result = await signup(
            db=db_session,
            data=SignupRequest(
                name="Dr. Rajesh",
                email="rajesh@college.edu",
                password="SecurePass123",
                role="teacher",
            ),
        )

        assert result["user"]["role"] == "teacher"
        assert result["user"]["status"] == "pending"

        row = await db_session.execute(
            select(User).where(User.email == "rajesh@college.edu")
        )
        user = row.scalar_one()
        assert user.role.value == "teacher"
        assert user.status.value == "pending"

    async def test_raises_on_duplicate_email(self, db_session):
        from app.services.auth import signup

        await signup(
            db=db_session,
            data=SignupRequest(
                name="Priya Singh",
                email="priya.singh@college.edu",
                password="SecurePass123",
                role="student",
            ),
        )

        with pytest.raises(Exception) as exc:
            await signup(
                db=db_session,
                data=SignupRequest(
                    name="Priya Singh",
                    email="priya.singh@college.edu",
                    password="SecurePass123",
                    role="student",
                ),
            )
        assert "already" in str(exc.value).lower() or "409" in str(exc.value)


class TestLoginRealDB:
    async def test_returns_tokens(self, db_session):
        from app.services.auth import signup, login

        await signup(
            db=db_session,
            data=SignupRequest(
                name="Priya Singh",
                email="priya.singh@college.edu",
                password="SecurePass123",
                role="student",
            ),
        )

        result = await login(
            db=db_session,
            email="priya.singh@college.edu",
            password="SecurePass123",
        )

        assert result["user"]["email"] == "priya.singh@college.edu"
        assert result["accessToken"] is not None
        assert result["refreshToken"] is not None

    async def test_raises_on_wrong_password(self, db_session):
        from app.services.auth import signup, login

        await signup(
            db=db_session,
            data=SignupRequest(
                name="Priya Singh",
                email="priya.singh@college.edu",
                password="SecurePass123",
                role="student",
            ),
        )

        with pytest.raises(Exception) as exc:
            await login(
                db=db_session,
                email="priya.singh@college.edu",
                password="wrong-password",
            )
        assert "Invalid" in str(exc.value)

    async def test_raises_on_user_not_found(self, db_session):
        from app.services.auth import login

        with pytest.raises(Exception) as exc:
            await login(
                db=db_session,
                email="nonexistent@college.edu",
                password="SecurePass123",
            )
        assert "not found" in str(exc.value).lower()
