import uuid
from datetime import datetime
from pydantic import ValidationError
import pytest


class TestNotificationOut:
    def test_valid_notification_out(self):
        from app.schemas.notification import NotificationOut

        data = NotificationOut(
            id=str(uuid.uuid4()),
            type="registration_accepted",
            title="Registration Accepted",
            message="You have been accepted",
            is_read=False,
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        assert data.type == "registration_accepted"
        assert data.is_read is False
        assert data.related_entity_type is None

    def test_with_related_entity(self):
        from app.schemas.notification import NotificationOut

        data = NotificationOut(
            id=str(uuid.uuid4()),
            type="event_approved",
            title="Event Approved",
            message="Your event was approved",
            related_entity_type="event",
            related_entity_id=str(uuid.uuid4()),
            is_read=True,
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        assert data.related_entity_type == "event"
        assert data.is_read is True

    def test_rejects_missing_required(self):
        from app.schemas.notification import NotificationOut

        with pytest.raises(ValidationError):
            NotificationOut()


class TestUnreadCountResponse:
    def test_valid(self):
        from app.schemas.notification import UnreadCountResponse

        data = UnreadCountResponse(count=5)
        assert data.count == 5


class TestMarkReadAllResponse:
    def test_valid(self):
        from app.schemas.notification import MarkReadAllResponse

        data = MarkReadAllResponse(count=10)
        assert data.count == 10
