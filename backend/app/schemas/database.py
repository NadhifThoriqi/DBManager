from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..services import pydatabase as pyd

# ──────────────────────────────────────────────
# REQUEST MODELS
# ──────────────────────────────────────────────

class CreateSQLiteRequest(BaseModel):
    db_name: str = Field(..., description="Nama file database SQLite (tanpa ekstensi .db)")


class CreateServerDBRequest(BaseModel):
    db_name: str = Field(..., description="Nama database yang akan dibuat")


class DeleteSQLiteRequest(BaseModel):
    db_name: str = Field(..., description="Nama file database SQLite (sertakan ekstensi .db)")


class DeleteServerDBRequest(BaseModel):
    db_name: str = Field(..., description="Nama database yang akan dihapus")

    @field_validator("db_name")
    def validate_db_name(cls, value: str) -> str:
        # Panggil fungsi validasi Anda di sini
        # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pyd.validate_db_name(value)


# ──────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ShowSQLiteResponse(BaseModel):
    total: int
    databases: list[Any]


class ShowServerDBResponse(BaseModel):
    total: int
    databases: list[str]

