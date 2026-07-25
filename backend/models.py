from datetime import datetime
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, JSON
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")   # "user" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable : les allocations créées avant l'authentification n'ont pas
    # de propriétaire tant que create_admin.py ne les a pas rattachées.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(String, nullable=False)               # ex: "27JUN26"
    label = Column(String, nullable=False)              # "Pre-Allocation" | "Allocation" | "Update 1" …
    type = Column(String, nullable=False)               # "prealloc" | "alloc_finale" | "creation" | "maj"
    docx_path = Column(String, nullable=True)
    source_pdf_path = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("allocations.id"), nullable=True)
    highlight_color_index = Column(Integer, default=0)  # 0=yellow 1=green 2=cyan 3=pink
    highlights_json = Column(JSON, nullable=True)       # [{"flt_no": str, "color_index": int}]
    changes_count = Column(Integer, default=0)          # nb de vols surlignés
    created_at = Column(DateTime, default=datetime.utcnow)
