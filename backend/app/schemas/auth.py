from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v):
        if len(v.encode()) > 72: raise ValueError("password must be at most 72 bytes")   # bcrypt limit
        return v
class LoginIn(BaseModel):
    email: EmailStr; password: str
class UserOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int; name: str; email: EmailStr; role: str; created_at: datetime
class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserOut
