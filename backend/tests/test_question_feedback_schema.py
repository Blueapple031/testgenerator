import pytest
from pydantic import ValidationError

from app.schemas.feedback import QuestionFeedbackRequest


def test_up_rating_clears_reason_and_comment():
    payload = QuestionFeedbackRequest(
        rating="up",
        reason_tags=["unclear_stem"],
        comment="should be cleared",
    )
    assert payload.rating == "up"
    assert payload.reason_tags == []
    assert payload.comment is None


def test_down_requires_reason_or_comment():
    with pytest.raises(ValidationError) as exc:
        QuestionFeedbackRequest(rating="down")
    assert "사유" in str(exc.value)


def test_down_accepts_reason_tags():
    payload = QuestionFeedbackRequest(rating="down", reason_tags=["off_topic", "poor_choices"])
    assert payload.reason_tags == ["off_topic", "poor_choices"]


def test_down_accepts_comment_only():
    payload = QuestionFeedbackRequest(rating="down", comment="정답이 이상해요")
    assert payload.comment == "정답이 이상해요"


def test_invalid_reason_tag_rejected():
    with pytest.raises(ValidationError):
        QuestionFeedbackRequest(rating="down", reason_tags=["unknown_reason"])
