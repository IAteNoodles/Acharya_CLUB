import pytest
from pydantic import ValidationError


class TestSuccessResponse:
    def test_valid(self):
        from app.schemas.common import SuccessResponse

        data = SuccessResponse(data={"key": "value"})
        assert data.success is True
        assert data.data == {"key": "value"}


class TestPaginatedMeta:
    def test_valid(self):
        from app.schemas.common import PaginatedMeta

        data = PaginatedMeta(page=1, limit=20, total=100, total_pages=5)
        assert data.page == 1
        assert data.total_pages == 5

    def test_rejects_missing_fields(self):
        from app.schemas.common import PaginatedMeta

        with pytest.raises(ValidationError):
            PaginatedMeta()


class TestPaginatedResponse:
    def test_valid(self):
        from app.schemas.common import PaginatedResponse, PaginatedMeta

        data = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            meta=PaginatedMeta(page=1, limit=20, total=2, total_pages=1),
        )
        assert data.success is True
        assert len(data.data) == 2
        assert data.meta.total == 2

    def test_empty_list(self):
        from app.schemas.common import PaginatedResponse, PaginatedMeta

        data = PaginatedResponse(
            data=[],
            meta=PaginatedMeta(page=1, limit=20, total=0, total_pages=0),
        )
        assert data.data == []


class TestErrorDetail:
    def test_valid(self):
        from app.schemas.common import ErrorDetail

        data = ErrorDetail(field="email", message="Invalid format")
        assert data.field == "email"
        assert data.message == "Invalid format"


class TestErrorResponse:
    def test_valid(self):
        from app.schemas.common import ErrorResponse

        data = ErrorResponse(error={"code": "NOT_FOUND", "message": "User not found"})
        assert data.success is False
        assert data.error["code"] == "NOT_FOUND"
