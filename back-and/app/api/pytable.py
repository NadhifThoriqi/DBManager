"""
==============
api/api_table.py
==============
FastAPI APIRouter untuk operasi tabel database.
Hanya berisi definisi endpoint dan request/response model.
Seluruh logika bisnis ada di services/pytable.py.

Endpoint:
    POST   /table/list
    POST   /table/structure
    POST   /table/content
    POST   /table/create
    POST   /table/column/add
    POST   /table/insert
    PUT    /table/update
    DELETE /table/row
    DELETE /table/clear
    DELETE /table/drop
"""

from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator, ValidationInfo

from ..core.enums import Indeks
from ..services import pydatabase as pd, pytable as pt, auth

router = APIRouter(prefix="/table", tags=["Table Operations"])


# ──────────────────────────────────────────────
# HELPER: Buat engine dari config request
# ──────────────────────────────────────────────

async def _get_engine(
    db_type: str,
    db_name: str,
    host: Optional[str],
    port: Optional[int],
    user: Optional[str],
    password: Optional[str],
):
    """Buat engine SQLAlchemy sesuai db_type."""
    ge = pt.GetEngine(
        db_name=db_name,
        host=host or "localhost",
        port=port,
        user=user or "root",
        password=password or "",
    )
    db_type_lower = db_type.lower()
    if db_type_lower == "sqlite":
        return await ge.sqlite()
    elif db_type_lower == "mysql":
        return await ge.mysql()
    elif db_type_lower == "postgresql":
        return await ge.postgresql()
    else:
        raise ValueError(
            f"db_type tidak dikenal: '{db_type}'. Pilih: sqlite | mysql | postgresql"
        )


# ──────────────────────────────────────────────
# HELPER: Konversi tipe string → SQLAlchemy type
# ──────────────────────────────────────────────

# Contoh yang robust:
def _resolve_column_type(type_str: str):
    from sqlalchemy import Integer, Float, Boolean, Text, String, Numeric, Date, DateTime
    t = type_str.strip().upper()
    if t in ("INTEGER", "INT"):
        return Integer()
    elif t in ("FLOAT", "REAL", "DOUBLE"):
        return Float()
    elif t in ("BOOLEAN", "BOOL"):
        return Boolean()
    elif t == "TEXT":
        return Text()
    elif t in ("NUMERIC", "DECIMAL"):
        return Numeric()
    elif t == "DATE":
        return Date()
    elif t in ("DATETIME", "TIMESTAMP"):
        return DateTime()
    elif t.startswith("VARCHAR"):
        try:
            length = int(t.replace("VARCHAR", "").strip("() "))
        except (ValueError, AttributeError):
            length = 255
        return String(length)
    else:
        return Text()


# ──────────────────────────────────────────────
# SHARED BASE REQUEST MODEL
# ──────────────────────────────────────────────

class EngineConfig(BaseModel):
    """Konfigurasi koneksi database yang digunakan di semua request."""
    db_type: Literal["sqlite", "mysql", "postgresql"] = Field(
        ...,
        description="Jenis database: sqlite | mysql | postgresql",
    )
    db_name: str = Field(
        ...,
        description=(
            "Nama database atau path file SQLite. "
            "Contoh SQLite: 'toko.db' | MySQL/PgSQL: 'toko_db'"
        ),
    )
    host: Optional[str] = Field(default="localhost", description="Host server (MySQL/PgSQL)")
    port: Optional[int] = Field(default=None, description="Port server (MySQL/PgSQL)")

    @field_validator("port", mode="after")  # 1. Menggunakan string "port"
    def validate_port(cls, value: Optional[int], info: ValidationInfo) -> Optional[int]:
        # 2. Mengambil db_type dari objek info.data
        db_type = info.data.get("db_type")
        
        # Jika port tidak diisi (None), berikan port default berdasarkan db_type
        if value is None:
            if db_type == "mysql":
                return 3306
            elif db_type == "postgresql":
                return 5432
                
        return value  # Jangan lupa kembalikan nilainya kembali


# ──────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ListTablesResponse(BaseModel):
    total: int
    tables: List[str]


class TableStructureResponse(BaseModel):
    table_name: str = Depends(pd.validate_db_name)
    columns: List[Dict[str, Any]]


class TableContentResponse(BaseModel):
    table_name: str = Depends(pd.validate_db_name)
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


# ──────────────────────────────────────────────
# ENDPOINTS: INSPEKSI DATABASE
# ──────────────────────────────────────────────

@router.post(
    "/list",
    response_model=ListTablesResponse,
    summary="Daftar semua tabel",
    description="Mengambil semua nama tabel yang ada di database.",
)
async def list_tables(body: ListTablesRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> ListTablesResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        tables = await pt.list_tables(engine)
        return ListTablesResponse(total=len(tables), tables=tables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@router.post(
    "/structure",
    response_model=TableStructureResponse,
    summary="Lihat struktur kolom tabel",
    description="Menampilkan detail kolom: nama, tipe, primary key, nullable, default, dll.",
)
async def inspect_structure(body: InspectStructureRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> TableStructureResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        raw_columns = await pt.inspect_table_structure(engine, body.table_name)
        columns:List[Dict[str, Any]] = [
            {**col, "type": str(col["type"])}
            for col in raw_columns
        ]
        return TableStructureResponse(table_name=body.table_name, columns=columns)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@router.post(
    "/content",
    response_model=TableContentResponse,
    summary="Lihat isi data tabel",
    description="Mengambil baris data dari tabel dengan batas jumlah yang bisa dikonfigurasi.",
)
async def view_content(body: ViewContentRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> TableContentResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        rows = await pt.view_table_content(engine, body.table_name, limit=body.limit)
        return TableContentResponse(table_name=body.table_name, limit=body.limit, rows=rows)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


# ──────────────────────────────────────────────
# ENDPOINTS: DDL (Struktur Tabel)
# ──────────────────────────────────────────────

@router.post(
    "/create",
    response_model=MessageResponse,
    summary="Buat tabel baru",
    description=(
        "Membuat tabel baru secara dinamis. "
        "Kolom bernama 'id' otomatis dijadikan Primary Key."
    ),
)
async def create_table(body: CreateTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        if not body.columns_def:
            raise ValueError("Minimal satu kolom harus didefinisikan")
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))

        # Sekarang type_str[0] dijamin adalah Tipe SQL (str) dan type_str[1] adalah Indeks
        columns_def: Dict[str, Tuple[Any, Any]] = {
            col_name: (_resolve_column_type(col_data.type), col_data.index)
            for col_name, col_data in body.columns_def.items()
        }
        
        result = await pt.create_dynamic_table(engine, body.table_name, columns_def)
        return MessageResponse(message=result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post(
    "/column/add",
    response_model=MessageResponse,
    summary="Tambah kolom baru ke tabel",
    description="Menambah kolom baru ke tabel yang sudah ada menggunakan ALTER TABLE.",
)
async def add_column(body: AddColumnRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.add_new_column(engine, body.table_name, body.column_name, body.column_type)
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# ENDPOINTS: DML (Isi Data)
# ──────────────────────────────────────────────

@router.post(
    "/insert",
    response_model=MessageResponse,
    summary="Insert satu baris data",
    description="Menambahkan satu baris data ke dalam tabel (parameterized query, aman dari SQL Injection).",
)
async def insert_data(body: InsertDataRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.insert_dynamic_data(engine, body.table_name, body.data)
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.put(
    "/update",
    response_model=MessageResponse,
    summary="Update data di tabel",
    description=(
        "Memperbarui baris data dengan kondisi WHERE. "
        "Gunakan placeholder :nama di condition_str. "
        "Contoh: condition_str='id = :target_id', condition_params={\"target_id\": 1}."
    ),
)
async def update_data(body: UpdateDataRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.update_table_data(
            engine,
            body.table_name,
            body.update_values,
            body.condition_str,
            body.condition_params,
        )
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ──────────────────────────────────────────────
# ENDPOINTS: HAPUS DATA / TABEL
# ──────────────────────────────────────────────

@router.delete(
    "/row",
    response_model=MessageResponse,
    summary="Hapus satu baris data",
    description=(
        "Menghapus baris data berdasarkan kondisi WHERE. "
        "Contoh: condition_str='id = :target_id', condition_params={\"target_id\": 5}."
    ),
)
async def delete_row(body: DeleteRowRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.delete_one_row(
            engine, body.table_name, body.condition_str, body.condition_params
        )
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/clear",
    response_model=MessageResponse,
    summary="Kosongkan semua data di tabel",
    description=(
        "Menghapus seluruh isi data di tabel TANPA menghapus struktur tabelnya. "
        "SQLite: DELETE FROM. MySQL/PostgreSQL: TRUNCATE TABLE."
    ),
)
async def clear_table(body: ClearTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.clear_table_data(engine, body.table_name, db_type=auth.TypeDB(body.db_type))
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.delete(
    "/drop",
    response_model=MessageResponse,
    summary="Hapus tabel secara permanen",
    description="⚠️ Menghapus tabel beserta seluruh datanya secara permanen. Tidak dapat dibatalkan!",
)
async def drop_table(body: DropTableRequest, payload: Dict[str, Any] = Depends(auth.get_cookie)) -> MessageResponse:
    try:
        engine = await _get_engine(body.db_type, body.db_name, body.host, body.port, payload.get("sub"), payload.get("pw"))
        result = await pt.drop_table(engine, body.table_name, auth.TypeDB(payload.get("db")))
        return MessageResponse(message=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")