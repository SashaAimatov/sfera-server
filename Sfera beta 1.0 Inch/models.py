from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RegisterReq(BaseModel):
    email: str
    username: str
    password: str
    display_name: Optional[str] = None


class LoginReq(BaseModel):
    login: str
    password: str


class UpdateProfileReq(BaseModel):
    display_name: str
    bio: Optional[str] = ""
    avatar_color: Optional[str] = None
    banner_style: Optional[str] = None


class CreatePostReq(BaseModel):
    content: Optional[str] = ""
    media_url: Optional[str] = None
    media_type: Optional[str] = None


class CommentReq(BaseModel):
    content: str


class MessageReq(BaseModel):
    content: str


class ImportPayload(BaseModel):
    tables: Dict[str, List[Dict[str, Any]]]
