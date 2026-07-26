from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Utilisateurs / authentification
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class UserSelfUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class UserAdminUpdate(BaseModel):
    role: Optional[Literal["user", "admin"]] = None
    is_active: Optional[bool] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------

class AdminUserOut(UserOut):
    alloc_count: int = 0


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["user", "admin"] = "user"


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[Literal["user", "admin"]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class TopUser(BaseModel):
    full_name: str
    email: EmailStr
    alloc_count: int


class AllocsByType(BaseModel):
    creation: int = 0
    prealloc: int = 0
    alloc_finale: int = 0
    maj: int = 0


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_allocs: int
    allocs_last_7_days: int
    allocs_by_type: AllocsByType
    top_users: list[TopUser]


class AdminAllocationOut(BaseModel):
    id: int
    label: str
    date: str
    type: str
    user_email: Optional[EmailStr] = None
    user_name: Optional[str] = None
    created_at: datetime
    docx_path: Optional[str] = None


class AdminAllocationPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AdminAllocationOut]


# ---------------------------------------------------------------------------
# Allocations
# ---------------------------------------------------------------------------

class AllocationBase(BaseModel):
    date: str
    label: str
    type: str
    docx_path: Optional[str] = None
    source_pdf_path: Optional[str] = None
    parent_id: Optional[int] = None
    highlight_color_index: int = 0


class AllocationCreate(AllocationBase):
    pass


class AllocationUpdate(BaseModel):
    label: Optional[str] = None
    docx_path: Optional[str] = None


class AllocationOut(AllocationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
