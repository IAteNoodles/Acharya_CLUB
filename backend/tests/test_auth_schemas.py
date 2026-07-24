import pytest
from pydantic import ValidationError
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)


class TestSignupRequest:
    def test_accepts_valid_student_data(self):
        data = SignupRequest(
            name="Priya Singh",
            email="priya.singh@college.edu",
            password="SecurePass123",
            role="student",
        )
        assert data.name == "Priya Singh"
        assert data.email == "priya.singh@college.edu"
        assert data.role == "student"

    def test_trims_name(self):
        data = SignupRequest(
            name="  Priya Singh  ",
            email="priya.singh@college.edu",
            password="SecurePass123",
            role="student",
        )
        assert data.name == "Priya Singh"

    def test_rejects_name_shorter_than_2_chars(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="A",
                email="test@college.edu",
                password="SecurePass123",
                role="student",
            )
        assert "at least 2" in str(exc.value)

    def test_rejects_name_longer_than_120_chars(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="A" * 121,
                email="test@college.edu",
                password="SecurePass123",
                role="student",
            )

    def test_lowercases_email(self):
        data = SignupRequest(
            name="Priya Singh",
            email="Priya.Singh@College.EDU",
            password="SecurePass123",
            role="student",
        )
        assert data.email == "priya.singh@college.edu"

    def test_trims_email(self):
        data = SignupRequest(
            name="Priya Singh",
            email="  priya.singh@college.edu  ",
            password="SecurePass123",
            role="student",
        )
        assert data.email == "priya.singh@college.edu"

    def test_rejects_non_college_email(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="Test User",
                email="test@gmail.com",
                password="SecurePass123",
                role="student",
            )
        assert "@college.edu" in str(exc.value)

    def test_rejects_invalid_email_format(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="not-an-email",
                password="SecurePass123",
                role="student",
            )

    def test_rejects_password_shorter_than_8_chars(self):
        with pytest.raises(ValidationError) as exc:
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="Short1",
                role="student",
            )
        assert "at least 8" in str(exc.value)

    def test_rejects_password_longer_than_100_chars(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="A" * 101,
                role="student",
            )

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            SignupRequest(
                name="Test User",
                email="test@college.edu",
                password="SecurePass123",
                role="admin",
            )

    def test_accepts_teacher_role(self):
        data = SignupRequest(
            name="Dr. Rajesh",
            email="rajesh@college.edu",
            password="SecurePass123",
            role="teacher",
        )
        assert data.role == "teacher"


class TestLoginRequest:
    def test_accepts_valid_data(self):
        data = LoginRequest(email="test@college.edu", password="password123")
        assert data.email == "test@college.edu"
        assert data.password == "password123"

    def test_lowercases_email(self):
        data = LoginRequest(email="Test@College.edu", password="password123")
        assert data.email == "test@college.edu"

    def test_rejects_missing_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="invalid", password="password123")

    def test_rejects_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="test@college.edu", password="")


class TestChangePasswordRequest:
    def test_accepts_valid_data(self):
        from app.schemas.auth import ChangePasswordRequest

        data = ChangePasswordRequest(currentPassword="OldPass123", newPassword="NewPass456")
        assert data.newPassword == "NewPass456"

    def test_rejects_empty_current_password(self):
        from app.schemas.auth import ChangePasswordRequest

        with pytest.raises(ValidationError):
            ChangePasswordRequest(currentPassword="", newPassword="NewPass456")

    def test_rejects_short_new_password(self):
        from app.schemas.auth import ChangePasswordRequest

        with pytest.raises(ValidationError) as exc:
            ChangePasswordRequest(currentPassword="OldPass123", newPassword="short")
        assert "at least 8" in str(exc.value)

    def test_rejects_long_new_password(self):
        from app.schemas.auth import ChangePasswordRequest

        with pytest.raises(ValidationError):
            ChangePasswordRequest(currentPassword="OldPass123", newPassword="A" * 101)


class TestRefreshRequest:
    def test_accepts_valid_token(self):
        data = RefreshRequest(refreshToken="some-refresh-token-value")
        assert data.refreshToken == "some-refresh-token-value"

    def test_rejects_empty_token(self):
        with pytest.raises(ValidationError):
            RefreshRequest(refreshToken="")

    def test_rejects_missing_token(self):
        with pytest.raises(ValidationError):
            RefreshRequest()


class TestTokenResponse:
    def test_creates_with_all_fields(self):
        data = TokenResponse(
            accessToken="access-value",
            refreshToken="refresh-value",
        )
        assert data.accessToken == "access-value"
        assert data.refreshToken == "refresh-value"


class TestUserResponse:
    def test_creates_with_all_fields(self):
        data = UserResponse(
            id="user-id",
            name="Priya Singh",
            email="priya.singh@college.edu",
            role="student",
            status="active",
        )
        assert data.id == "user-id"
        assert data.role == "student"
