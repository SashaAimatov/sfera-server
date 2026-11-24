from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    login: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=50)
    bio: Optional[str] = Field(default=None, max_length=200)


class PostRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
