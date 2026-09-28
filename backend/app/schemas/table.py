from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

from ..core.enums import Indeks
from ..services import pydatabase as pd


# ──────────────────────────────────────────────
# SHARED BASE REQUEST MODEL
# ──────────────────────────────────────────────

class EngineConfig(BaseModel):
    """Konfigurasi koneksi database yang digunakan di semua request."""
    db_name: str = Field(
        ...,
        description=(
            "Nama database atau path file SQLite. "
            "Contoh SQLite: 'toko.db' | MySQL/PgSQL: 'toko_db'"
        ),
    )


# ──────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ListTablesResponse(BaseModel):
    total: int
    tables: List[str]


class TableStructureResponse(BaseModel):
    table_name: str
    columns: List[Dict[str, Any]]


class TableContentResponse(BaseModel):
    table_name: str
    limit: int
    rows: List[Dict[str, Any]]


# ──────────────────────────────────────────────
# REQUEST BODY MODELS
# ──────────────────────────────────────────────

class ListTablesRequest(EngineConfig):
    pass


class InspectStructureRequest(EngineConfig):
    table_name: str = Field(
        ..., 
        description="Nama tabel yang ingin di-inspect"
    )

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
        # Panggil fungsi validasi Anda di sini
        # Contoh sederhana: pastikan tidak mengandung karakter aneh
        return pd.validate_db_name(value)
    

class ViewContentRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    limit: int = Field(
        default=10, ge=1, le=1000,
        description="Jumlah baris maksimum yang diambil (1–1000, default: 10)",
    )

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
        # Panggil fungsi validasi Anda di sini
        # Contoh sederhana: pastikan tidak mengandung karakter aneh
        return pd.validate_db_name(value)


# BUAT SUB-MODEL BARU UNTUK STRUKTUR KOLOM
class ColumnDefinition(BaseModel):
    type: str = Field(
        ..., 
        description="Tipe data SQL, contoh: VARCHAR(100), INTEGER, FLOAT"
    )
    index: Indeks = Field(
        default=Indeks.NONE, 
        description="Tipe indeks untuk kolom ini"
    )


# UTAMA: Model Request Pembuatan Tabel
class CreateTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel baru yang akan dibuat")
    
    # Gunakan ColumnDefinition sebagai tipe value di dalam Dictionary
    columns_def: Dict[str, ColumnDefinition] = Field(
        ...,
        description="Definisi kolom: {nama_kolom: {type: tipe_sql, index: jenis_indeks}}.",
        examples=[{
            "id": {"type": "INTEGER", "index": "primary"},
            "nama": {"type": "VARCHAR(100)", "index": ""},
            "harga": {"type": "FLOAT", "index": ""},
            "stok": {"type": "INTEGER", "index": ""},
            "is_aktif": {"type": "BOOLEAN", "index": ""},
        }]
    )
    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class AddColumnRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan ditambah kolomnya")
    column_name: str = Field(..., description="Nama kolom baru")
    column_type: str = Field(
        ...,
        description="Tipe SQL kolom mentah, contoh: 'TEXT', 'VARCHAR(50)', 'INTEGER'",
    )

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class InsertDataRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel tujuan")
    data: Dict[str, Any] = Field(
        ...,
        description="Data yang akan diinsert: {nama_kolom: nilai}",
        examples=[{"nama": "Laptop ASUS", "harga": 12500000.0, "stok": 15, "is_aktif": True},]
    )

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class UpdateDataRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    update_values: Dict[str, Any] = Field(
        ...,
        description="Data yang akan diperbarui: {nama_kolom: nilai_baru}",
        examples=[{"stok": 50, "harga": 11000000.0},]
    )
    condition_str: str = Field(
        ...,
        description="Kondisi WHERE dengan placeholder SQLAlchemy, contoh: 'id = :target_id'",
    )
    condition_params: Dict[str, Any] = Field(
        ...,
        description="Nilai untuk placeholder, contoh: {\"target_id\": 1}",
    )
    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class DeleteRowRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel")
    condition_str: str = Field(
        ...,
        description="Kondisi WHERE dengan placeholder, contoh: 'id = :target_id'",
    )
    condition_params: Dict[str, Any] = Field(
        ...,
        description="Nilai untuk placeholder, contoh: {\"target_id\": 3}",
    )
    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class ClearTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan dikosongkan datanya")

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)


class DropTableRequest(EngineConfig):
    table_name: str = Field(..., description="Nama tabel yang akan dihapus secara permanen")

    @field_validator("table_name")
    def validate_table_name(cls, value: str) -> str:
    # Panggil fungsi validasi Anda di sini
    # Contoh sederhana: pastikan tidak mengandung karakter aneh    
        return pd.validate_db_name(value)
