from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=10,
        max_length=512,
        description="JWT refresh token"
    )


class UserUpdatePasswordRequest(BaseModel):
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)"
    )




class UserCreateRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="User username"
    )
    email: EmailStr = Field(
        ...,
        max_length=254,
        description="User email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password"
    )
    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )
        return value


class AccessTokenResponse(BaseModel):
    token_type: str = Field(
        default="Bearer",
        min_length=3,
        max_length=20
    )
    access_token: str = Field(
        ...,
        min_length=10,
        max_length=512
    )
    expires_at: int = Field(
        ...,
        gt=0,
        description="Unix timestamp"
    )
    refresh_token: str = Field(
        ...,
        min_length=10,
        max_length=512
    )
    refresh_token_expires_at: int = Field(
        ...,
        gt=0,
        description="Unix timestamp"
    )

    model_config = ConfigDict(from_attributes=True)



class UserResponse(BaseModel):
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=64
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50
    )
    email: EmailStr = Field(
        ...,
        max_length=254
    )

    model_config = ConfigDict(from_attributes=True)


class ModelRequest(BaseModel):
    text: str
    model_config = ConfigDict(from_attributes=True)

class ModelResponse(BaseModel):
    prediction: str
    model_config = ConfigDict(from_attributes=True)