"""
Pydantic models for SeerrBridge
"""
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, List, Dict, Any

class MediaInfo(BaseModel):
    media_type: str
    tmdbId: int
    tvdbId: Optional[int] = Field(default=None, alias='tvdbId')
    status: str
    status4k: str

    @field_validator('tvdbId', mode='before')
    @classmethod
    def empty_string_to_none(cls, value):
        if value == '':
            return None
        return value

class RequestInfo(BaseModel):
    request_id: str
    requestedBy_email: str
    requestedBy_username: str
    requestedBy_avatar: str
    requestedBy_settings_discordId: Optional[str] = None
    requestedBy_settings_telegramChatId: Optional[str] = None

class IssueInfo(BaseModel):
    issue_id: str
    issue_type: str
    issue_status: str
    reportedBy_email: str
    reportedBy_username: str
    reportedBy_avatar: str
    reportedBy_settings_discordId: str
    reportedBy_settings_telegramChatId: str

class CommentInfo(BaseModel):
    comment_message: str
    commentedBy_email: str
    commentedBy_username: str
    commentedBy_avatar: str
    commentedBy_settings_discordId: str
    commentedBy_settings_telegramChatId: str

class WebhookPayload(BaseModel):
    notification_type: str
    event: str
    subject: str
    message: Optional[str] = None
    image: Optional[str] = None
    media: Optional[MediaInfo] = None
    request: Optional[RequestInfo] = None
    issue: Optional[IssueInfo] = None
    comment: Optional[CommentInfo] = None
    extra: List[Dict[str, Any]] = [] 