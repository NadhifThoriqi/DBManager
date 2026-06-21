"""
==========
pytable.py
==========
Modul utilitas untuk operasi database (SQLite, MySQL, PostgreSQL)
menggunakan SQLModel + SQLAlchemy.

Dependensi:
    pip install sqlmodel aiosqlite asyncmy asyncpg  # pilih sesuai kebutuhan, jangan install semua kecuali diperlukan

Struktur Modul:
    - Config          : Konfigurasi koneksi database
    - GetEngine       : Factory untuk membuat engine sesuai jenis DB
    - list_tables     : Ambil daftar semua tabel
    - inspect_table_structure : Lihat struktur kolom tabel
    - view_table_content      : Lihat isi data tabel
    - create_dynamic_table    : Buat tabel baru secara dinamis
    - insert_dynamic_data     : Tambah satu baris data
    - add_new_column          : Tambah kolom baru (ALTER TABLE)
    - update_table_data       : Update data dengan kondisi WHERE
    - clear_table_data        : Kosongkan isi tabel (bukan hapus)
    - drop_table              : Hapus tabel secara permanen
"""

from typing import List, Optional, Any, Dict
from sqlmodel import SQLModel, text
from sqlalchemy import Connection, CursorResult, MetaData, Table, Column, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker

# Import validator nama tabel/db dari modul lain dalam package ini
from .pydatabase import validate_db_name
from .auth import TypeDB
from ..core.enums import Indeks

# ──────────────────────────────────────────────
# KONFIGURASI & ENGINE
# ──────────────────────────────────────────────

class Config(SQLModel):
    """
    Model konfigurasi koneksi database.

    Contoh penggunaan:
    ------------------
    cfg = Config(
        host="localhost",
        port=3306,
        user="root",
        password="secret",
        database="toko_db"
    )
    """
    host: str
    port: int
    user: str
    password: str
    database: str


class GetEngine:
    """
    Factory class untuk membuat SQLAlchemy Engine sesuai jenis database.

    Port default:
        - MySQL      : 3306
        - PostgreSQL : 5432
        - SQLite     : tidak pakai host/port (path file .db)

    Contoh penggunaan:
    ------------------
    # SQLite
    engine = await GetEngine(db_name="data/toko.db").sqlite()

    # MySQL
    engine = await GetEngine(
        db_name="toko_db",
        host="localhost",
        port=3306,
        user="root",
        password="secret"
    ).mysql()

    # PostgreSQL
    engine = await GetEngine(
        db_name="toko_db",
        host="localhost",
        port=5432,
        user="postgres",
        password="secret"
    ).postgresql()
    """

    def __init__(
        self,
        db_name: str,
        host: Optional[str] = "localhost",
        port: Optional[int] = None,
        user: Optional[str] = "root",
        password: Optional[str] = "",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name

    async def sqlite(self) -> AsyncEngine:
        """
        Buat engine untuk SQLite.
        db_name = path ke file .db, contoh: 'data/toko.db' atau ':memory:'
        """
        return create_async_engine(
            f"sqlite+aiosqlite:///{self.db_name}",
        )

    async def mysql(self) -> AsyncEngine:
        """
        Buat engine untuk MySQL / MariaDB.
        Membutuhkan asyncmy: pip install asyncmy
        """
        if not self.port:
            self.port = 3306
        return create_async_engine(
            f"mysql+asyncmy://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}",
            echo=False,           # Set True untuk melihat query SQL di terminal (opsional)
            pool_recycle=3600,   # Mencegah disconnect otomatis dari MySQL
            pool_pre_ping=True   # Memastikan koneksi valid sebelum mengeksekusi query
        )

    async def postgresql(self) -> AsyncEngine:
        """
        Buat engine untuk PostgreSQL.
        Membutuhkan psycopg2: pip install asyncpg
        """
        if not self.port:
            self.port = 5432
        return create_async_engine(
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}",
            pool_pre_ping=True   # Memastikan koneksi valid sebelum mengeksekusi query
        )


# ──────────────────────────────────────────────
# INSPEKSI DATABASE
# ──────────────────────────────────────────────

async def list_tables(engine: AsyncEngine) -> List[str]:
    """
    Ambil daftar semua nama tabel yang ada di database.

    Parameters
    ----------
    engine : Engine
        Engine koneksi yang sudah dibuat via GetEngine.

    Returns
    -------
    List[str]
        Contoh: ['produk', 'pelanggan', 'transaksi']

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()
    tabel = list_tables(engine)
    print(tabel)
    # Output: ['produk', 'pelanggan', 'transaksi']
    """
    def execute_update_sync(sync_conn: Connection):
        inspector: Any = inspect(sync_conn)
        return inspector.get_table_names()

    async with engine.begin() as conn:
        list_table = await conn.run_sync(execute_update_sync)

    return list_table


async def inspect_table_structure(engine: AsyncEngine, table_name: str) -> List[Dict[str, Any]]:
    """
    Ambil detail struktur kolom dari sebuah tabel (seperti DESCRIBE di MySQL).

    Parameters
    ----------
    engine     : Engine  - koneksi database
    table_name : str     - nama tabel yang ingin di-inspect

    Returns
    -------
    List[Dict] berisi info kolom:
        {
            "name"          : nama kolom,
            "type"          : tipe data kolom (objek SQLAlchemy),
            "pk"            : "Y" jika primary key, "N" jika bukan,
            "nullable"      : True/False,
            "autoincrement" : True/False/None,
            "default"       : nilai default atau None,
            "comment"       : komentar kolom atau None
        }

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()
    struktur = inspect_table_structure(engine, "produk")
    for kolom in struktur:
        print(kolom)
    # Output:
    # {'name': 'id', 'type': INTEGER(), 'pk': 'Y', 'nullable': False, ...}
    # {'name': 'nama', 'type': VARCHAR(length=100), 'pk': 'N', 'nullable': True, ...}
    """
    def execute_structure_sync(sync_conn: Connection):
        inspector: Any = inspect(sync_conn)

        # 1. Ambil daftar kolom yang menjadi Primary Key pada tabel ini
        # Mengembalikan dict seperti: {'constrained_columns': ['id'], 'name': 'pk_user'}    
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = pk_constraint.get("constrained_columns", [])

        columns_info = inspector.get_columns(table_name)

        result: List[Dict[str, Any]] = []

        for col in columns_info:
            col_name = col["name"]
            
            result.append({
                "name":          col["name"],
                "type":          col["type"],
                "primary_key":   "Y" if col_name in pk_columns else None,
                "nullable":      col["nullable"],
                "autoincrement": col.get("autoincrement"),
                "default":       col["default"],
                "comment":       col.get("comment"),
            })

        return result
    
    async with engine.begin() as conn:
        result = await conn.run_sync(execute_structure_sync)

    return result


async def view_table_content(engine: AsyncEngine, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Ambil isi data dari tabel dalam bentuk list of dict.

    Parameters
    ----------
    engine     : Engine  - koneksi database
    table_name : str     - nama tabel
    limit      : int     - jumlah baris maksimum yang diambil (default: 5)

    Returns
    -------
    List[Dict]  -> setiap dict mewakili satu baris, key = nama kolom

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()
    data = view_table_content(engine, "produk", limit=3)
    for baris in data:
        print(baris)
    # Output:
    # {'id': 1, 'nama': 'Laptop', 'harga': 15000000.0, 'stok': 10}
    # {'id': 2, 'nama': 'Mouse', 'harga': 250000.0, 'stok': 50}
    # {'id': 3, 'nama': 'Keyboard', 'harga': 450000.0, 'stok': 30}
    """
    def execute_view_sync(sync_conn: Connection):
        inspector: Any = inspect(sync_conn)

        return [col["name"] for col in inspector.get_columns(table_name)]

    async with engine.begin() as conn:
        columns = await conn.run_sync(execute_view_sync)
        if not columns:
            return []

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) 
    async with async_session_maker() as session:
        query = text(f"SELECT * FROM {table_name} LIMIT :limit")
        result = await session.execute(query, {"limit": limit})

        # Di SQLAlchemy async, gunakan .mappings().all() untuk langsung mendapatkan format dict
        rows = result.mappings().all()

        if not rows:
            return []

        # Konversi setiap row (tuple) menjadi dict {nama_kolom: nilai}
        return [dict(row) for row in rows]


# ──────────────────────────────────────────────
# OPERASI DDL (Struktur Tabel)
# ──────────────────────────────────────────────

async def create_dynamic_table(engine: AsyncEngine, table_name: str, columns_def: Dict[str, Any]) -> str:
    """
    Buat tabel baru secara dinamis berdasarkan definisi kolom.

    Kolom bernama 'id' akan otomatis dijadikan Primary Key.

    Parameters
    ----------
    engine      : Engine        - koneksi database
    table_name  : str           - nama tabel baru
    columns_def : Dict[str,Any] - mapping {nama_kolom: tipe_SQLAlchemy}

    Returns
    -------
    str - pesan sukses

    Contoh penggunaan:
    ------------------
    from sqlalchemy import Integer, String, Float, Boolean

    engine = GetEngine("toko.db").sqlite()

    create_dynamic_table(
        engine,
        table_name="produk",
        columns_def={
            "id"       : Integer,       # ← otomatis jadi Primary Key
            "nama"     : String(100),
            "harga"    : Float,
            "stok"     : Integer,
            "is_aktif" : Boolean
        }
    )
    # Output: "Sukses: Tabel 'produk' berhasil dibuat!"
    """
    metadata = MetaData()
    safe_name = validate_db_name(table_name)

    columns: List[Column[Any]] = []
    for col_name, (col_type, col_index) in columns_def.items():
        # Inisialisasi status default sebagai boolean biasa
        is_pk = False
        is_idx = False
        is_uniq = False
        
        # Tentukan kondisi berdasarkan input
        if col_name.lower() == "id" or col_index == Indeks.PRIMARY:
            is_pk = True
        elif col_index == Indeks.UNIQUE:
            is_uniq = True
        elif col_index == Indeks.INDEX:
            is_idx = True
        elif col_index in (Indeks.FULLTEXT, Indeks.SPATIAL):
            is_idx = True 

        # Terjemahkan langsung secara eksplisit di sini. 
        # Pylance tidak akan bingung karena posisinya jelas.
        columns.append(
            Column(
                col_name, 
                col_type, 
                primary_key=is_pk, 
                index=is_idx, 
                unique=is_uniq
            )
        )

    # Daftarkan tabel ke metadata lalu buat di database fisik
    Table(safe_name, metadata, *columns)

    async with engine.begin() as conn:
        def create_tables(sync_conn: Connection):
            metadata.create_all(bind=sync_conn)

        await conn.run_sync(create_tables)

    return f"Sukses: Tabel '{safe_name}' berhasil dibuat!"


async def add_new_column(engine: AsyncEngine, table_name: str, column_name: str, column_type: str) -> str:
    """
    Tambah kolom baru ke tabel yang sudah ada (ALTER TABLE).

    ⚠️  column_name dan column_type harus berasal dari input internal
        (developer/sistem), bukan dari input pengguna akhir, untuk
        menghindari SQL Injection.

    Parameters
    ----------
    engine      : Engine - koneksi database
    table_name  : str    - nama tabel yang ingin diubah
    column_name : str    - nama kolom baru
    column_type : str    - tipe SQL mentah, misal: 'VARCHAR(100)', 'INTEGER', 'TEXT'

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    add_new_column(engine, "produk", "deskripsi", "TEXT")
    # Output: Sukses: Kolom 'deskripsi' (TEXT) berhasil ditambahkan ke tabel 'produk'.

    add_new_column(engine, "produk", "kategori", "VARCHAR(50)")
    # Output: Sukses: Kolom 'kategori' (VARCHAR(50)) berhasil ditambahkan ke tabel 'produk'.
    """
    def create_tables(sync_conn: Connection) -> bool:
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])
        return table_name in metadata.tables
    
    async with engine.begin() as conn:
        table_exists = await conn.run_sync(create_tables)

        if not table_exists:
            raise ValueError(f"Tabel '{table_name}' tidak dapat ditemukan.")
        
        query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        await conn.execute(query)

    return (
        f"Sukses: Kolom '{column_name}' ({column_type}) "
        f"berhasil ditambahkan ke tabel '{table_name}'."
    )


# ──────────────────────────────────────────────
# OPERASI DML (Isi Data)
# ──────────────────────────────────────────────

async def insert_dynamic_data(engine: AsyncEngine, table_name: str, data: Dict[str, Any]) -> str:
    """
    Tambahkan SATU baris data ke dalam tabel secara aman (anti SQL Injection).

    Parameters
    ----------
    engine     : Engine        - koneksi database
    table_name : str           - nama tabel tujuan
    data       : Dict[str,Any] - data yang akan dimasukkan {nama_kolom: nilai}

    Returns
    -------
    str - pesan sukses

    Catatan:
    --------
    - Kolom 'id' bisa dihilangkan jika sudah AUTOINCREMENT
    - Gunakan inspect_table_structure() untuk melihat struktur kolom terlebih dahulu

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    insert_dynamic_data(
        engine,
        table_name="produk",
        data={
            "nama"     : "Laptop ASUS",
            "harga"    : 12500000.0,
            "stok"     : 15,
            "is_aktif" : True
        }
    )
    # Output: "Sukses: Data berhasil ditambahkan ke tabel 'produk'."
    """
    def execute_insert_async(sync_conn: Connection):
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])

        if table_name not in metadata.tables:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

        target_table = metadata.tables[table_name]

        valid_columns = {col.name for col in target_table.columns}
        filter_data = {k: v for k, v in data.items() if k in valid_columns}

        if not filter_data:
            raise ValueError("Tidak ada kolom ynag cocok untuk dimasukkan ke dalam tabel")
            
        # insert().values() aman dari SQL Injection karena menggunakan parameterized query
        query = target_table.insert().values(**filter_data)
        sync_conn.execute(query)

    async with engine.begin() as conn:
        await conn.run_sync(execute_insert_async)
        
    return f"Sukses: Data berhasil ditambahkan ke tabel '{table_name}'."


async def update_table_data(engine: AsyncEngine, table_name: str, update_values: Dict[str, Any], condition_str: str, condition_params: Dict[str, Any]) -> str:
    """
    Perbarui isi data di tabel secara dinamis dengan kondisi WHERE.

    Menggunakan parameterized query untuk mencegah SQL Injection.

    Parameters
    ----------
    engine           : Engine        - koneksi database
    table_name       : str           - nama tabel
    update_values    : Dict[str,Any] - data yang diubah {nama_kolom: nilai_baru}
    condition_str    : str           - kondisi WHERE dalam format SQLAlchemy text,
                                       contoh: "id = :target_id"
    condition_params : Dict[str,Any] - nilai untuk placeholder di condition_str,
                                       contoh: {"target_id": 1}

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    # Update stok dan harga produk dengan id = 1
    update_table_data(
        engine,
        table_name      = "produk",
        update_values   = {"stok": 50, "harga": 11000000.0},
        condition_str   = "id = :target_id",
        condition_params= {"target_id": 1}
    )
    # Output: Sukses: 1 baris data pada tabel 'produk' berhasil diperbarui.

    # Update semua produk yang tidak aktif
    update_table_data(
        engine,
        table_name      = "produk",
        update_values   = {"is_aktif": False},
        condition_str   = "stok = :stok_habis",
        condition_params= {"stok_habis": 0}
    )
    """
    def execute_update_async(sync_conn: Connection):
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])

        if table_name not in metadata.tables:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan.")

        target_table = metadata.tables[table_name]

        valid_columns = {col.name for col in target_table.columns}
        filtered_updates = {k : v for k, v in update_values.items() if k in valid_columns}

        if not filtered_updates:
            raise ValueError("Tidak ada kolom yang diberikan untuk diperbarui.")

        query = target_table.update().where(text(condition_str)).values(**filtered_updates)

        result: CursorResult[Any] = sync_conn.execute(query, condition_params)

        return result.rowcount

    async with engine.begin() as conn:
        row_count = await conn.run_sync(execute_update_async)

    return (
        f"Sukses: {row_count} baris data pada tabel "
        f"'{table_name}' berhasil diperbarui."
    )

# ──────────────────────────────────────────────
# OPERASI HAPUS DATA / TABEL
# ──────────────────────────────────────────────

async def delete_one_row(engine: AsyncEngine, table_name: str, condition_str: str, condition_params: Dict[str, Any]) -> str:
    """
    Hapus SATU baris data dari tabel berdasarkan kondisi WHERE.

    Menggunakan parameterized query untuk mencegah SQL Injection.
    Jika kondisi cocok dengan lebih dari satu baris, HANYA satu baris
    pertama yang akan dihapus (menggunakan LIMIT 1 untuk SQLite/MySQL).
    Untuk PostgreSQL, gunakan primary key agar lebih aman.

    Parameters
    ----------
    engine           : Engine        - koneksi database
    table_name       : str           - nama tabel
    condition_str    : str           - kondisi WHERE dengan placeholder,
                                       contoh: "id = :target_id"
    condition_params : Dict[str,Any] - nilai untuk placeholder,
                                       contoh: {"target_id": 5}

    Returns
    -------
    str - pesan sukses beserta jumlah baris yang terhapus

    Raises
    ------
    ValueError - jika tabel tidak ditemukan
    ValueError - jika kondisi tidak cocok dengan baris manapun

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    # Hapus produk dengan id = 3
    delete_one_row(
        engine,
        table_name       = "produk",
        condition_str    = "id = :target_id",
        condition_params = {"target_id": 3}
    )
    # Output: "Sukses: 1 baris data dengan kondisi 'id = :target_id' berhasil dihapus dari tabel 'produk'."

    # Hapus produk berdasarkan nama
    delete_one_row(
        engine,
        table_name       = "produk",
        condition_str    = "nama = :target_nama",
        condition_params = {"target_nama": "Laptop ASUS"}
    )
    # Output: "Sukses: 1 baris data dengan kondisi 'nama = :target_nama' berhasil dihapus dari tabel 'produk'."
    """
    def execute_delete_one_sync(sync_conn: Connection):
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])

        if table_name not in metadata.tables:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

        target_table = metadata.tables[table_name]

        query = target_table.delete().where(text(condition_str))
        
        result: CursorResult[Any] = sync_conn.execute(query, condition_params)
        return result.rowcount

    async with engine.begin() as conn:
        rowcount = await conn.run_sync(execute_delete_one_sync)

        if rowcount == 0:
            raise ValueError(
                f"Tidak ada data yang cocok dengan kondisi '{condition_str}' "
                f"di tabel '{table_name}'. Tidak ada baris yang dihapus."
            )

    return (
        f"Sukses: {rowcount} baris data dengan kondisi '{condition_str}' "
        f"berhasil dihapus dari tabel '{table_name}'."
    )


async def clear_table_data(engine: AsyncEngine, table_name: str, db_type: TypeDB) -> str:
    """
    Kosongkan semua isi data di tabel TANPA menghapus struktur tabelnya.

    - SQLite     : menggunakan DELETE FROM (TRUNCATE tidak didukung)
                   Auto-increment juga direset jika menggunakan sqlite_sequence
    - MySQL/PgSQL: menggunakan TRUNCATE TABLE (lebih cepat untuk data besar)

    Parameters
    ----------
    engine     : Engine                            - koneksi database
    table_name : str                               - nama tabel
    db_type    : "sqlite" | "mysql" | "postgresql" - jenis database

    Returns
    -------
    str - pesan sukses

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    pesan = clear_table_data(engine, "produk", db_type="sqlite")
    print(pesan)
    # Output: "Sukses: Semua data di dalam tabel 'produk' berhasil dikosongkan."

    # Untuk MySQL:
    engine_mysql = GetEngine("toko_db", port=3306, password="secret").mysql()
    clear_table_data(engine_mysql, "produk", db_type="mysql")
    """
    def execute_clear_table_async(sync_conn: Connection):
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])

        if table_name not in metadata.tables:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

        dialect = conn.dialect
        safe_table_name = dialect.identifier_preparer.quote(table_name)

        if db_type.lower() == "sqlite":
            # SQLite tidak support TRUNCATE, gunakan DELETE FROM
            sync_conn.execute(text(f"DELETE FROM {safe_table_name}"))
            try:
                # Reset counter autoincrement (jika ada)
                sync_conn.execute(
                    text("DELETE FROM sqlite_sequence WHERE name = :tbl"),
                    {"tbl": safe_table_name}
                )
            except Exception:
                pass  # Abaikan jika tabel tidak pakai AUTOINCREMENT
        else:
            # MySQL dan PostgreSQL: TRUNCATE jauh lebih efisien untuk data besar
            sync_conn.execute(text(f"TRUNCATE TABLE {safe_table_name}"))

    async with engine.begin() as conn:
        await conn.run_sync(execute_clear_table_async)

    return f"Sukses: Semua data di dalam tabel '{table_name}' berhasil dikosongkan."


async def drop_table(engine: AsyncEngine, table_name: str, db_type: TypeDB) -> str:
    """
    Hapus tabel secara PERMANEN dari database (DROP TABLE).

    ⚠️  Operasi ini tidak dapat dibatalkan! Struktur tabel dan
        seluruh datanya akan hilang selamanya.

    Parameters
    ----------
    engine     : Engine - koneksi database
    table_name : str    - nama tabel yang akan dihapus

    Returns
    -------
    str - pesan sukses

    Contoh penggunaan:
    ------------------
    engine = GetEngine("toko.db").sqlite()

    pesan = drop_table(engine, "produk_lama")
    print(pesan)
    # Output: "Sukses: Tabel 'produk_lama' berhasil dihapus secara permanen!"
    """
    def execute_drop_sync(sync_conn: Connection):
        metadata = MetaData()
        metadata.reflect(bind=sync_conn, only=[table_name])

        if table_name not in metadata.tables:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

        dialect = sync_conn.dialect
        safe_table_name = dialect.identifier_preparer.quote(table_name)

        # Kondisikan query berdasarkan jenis database
        if db_type.lower() == "postgresql":
            # Postgres wajib pakai CASCADE jika ada relasi agar tidak error
            query_str = f"DROP TABLE {safe_table_name} CASCADE"
        else:
            # SQLite dan MySQL menggunakan perintah standar tanpa CASCADE
            query_str = f"DROP TABLE {safe_table_name}"
            
        sync_conn.execute(text(query_str))
        return True

    async with engine.begin() as conn:
        table_was_dropped = await conn.run_sync(execute_drop_sync)
        
        if not table_was_dropped:
            raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

    return f"Sukses: Tabel '{table_name}' berhasil dihapus secara permanen!"


# ──────────────────────────────────────────────
# CONTOH PENGGUNAAN LENGKAP (jalankan sebagai script)
# ──────────────────────────────────────────────
"""
if __name__ == "__main__":
    from sqlalchemy import Integer, String, Float, Boolean

    # 1. Buat engine SQLite (in-memory untuk testing)
    engine = GetEngine(db_name=":memory:").sqlite()
    print("Engine dibuat:", engine)

    # 2. Buat tabel 'produk'
    print(create_dynamic_table(
        engine,
        table_name="produk",
        columns_def={
            "id"       : Integer,
            "nama"     : String(100),
            "harga"    : Float,
            "stok"     : Integer,
            "is_aktif" : Boolean,
        }
    ))

    # 3. Lihat daftar tabel
    print("Tabel:", list_tables(engine))

    # 4. Lihat struktur tabel
    print("Struktur 'produk':")
    for col in inspect_table_structure(engine, "produk"):
        print(" ", col)

    # 5. Tambah kolom baru
    add_new_column(engine, "produk", "deskripsi", "TEXT")

    # 6. Insert data
    for row in [
        {"nama": "Laptop ASUS",  "harga": 12500000.0, "stok": 15, "is_aktif": True},
        {"nama": "Mouse Logitech","harga": 350000.0,  "stok": 50, "is_aktif": True},
        {"nama": "Keyboard Mech", "harga": 750000.0,  "stok": 0,  "is_aktif": False},
    ]:
        print(insert_dynamic_data(engine, "produk", row))

    # 7. Lihat isi tabel
    print("Isi tabel 'produk':")
    for baris in view_table_content(engine, "produk", limit=10):
        print(" ", baris)

    # 8. Update data
    update_table_data(
        engine,
        table_name       = "produk",
        update_values    = {"stok": 100, "harga": 11000000.0},
        condition_str    = "nama = :target_nama",
        condition_params = {"target_nama": "Laptop ASUS"},
    )

    # 9. Kosongkan tabel
    print(clear_table_data(engine, "produk", db_type="sqlite"))

    # 10. Hapus tabel
    print(drop_table(engine, "produk"))
"""