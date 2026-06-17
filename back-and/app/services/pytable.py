"""
==========
pytable.py
==========
Modul utilitas untuk operasi database (SQLite, MySQL, PostgreSQL)
menggunakan SQLModel + SQLAlchemy.

Dependensi:
    pip install sqlmodel pymysql psycopg2-binary

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

from typing import List, Optional, Any, Dict, Literal
from sqlmodel import create_engine, SQLModel, Session, text
from sqlalchemy import Engine, MetaData, Table, Column, inspect

# Import validator nama tabel/db dari modul lain dalam package ini
from .pydatabase import validate_db_name


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
    engine = GetEngine(db_name="data/toko.db").sqlite()

    # MySQL
    engine = GetEngine(
        db_name="toko_db",
        host="localhost",
        port=3306,
        user="root",
        password="secret"
    ).mysql()

    # PostgreSQL
    engine = GetEngine(
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

    def sqlite(self) -> Engine:
        """
        Buat engine untuk SQLite.
        db_name = path ke file .db, contoh: 'data/toko.db' atau ':memory:'
        """
        return create_engine(f"sqlite:///{self.db_name}")

    def mysql(self) -> Engine:
        """
        Buat engine untuk MySQL / MariaDB.
        Membutuhkan pymysql: pip install pymysql
        """
        if not self.port:
            self.port = 3306
        return create_engine(
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db_name}"
        )

    def postgresql(self) -> Engine:
        """
        Buat engine untuk PostgreSQL.
        Membutuhkan psycopg2: pip install psycopg2-binary
        """
        if not self.port:
            self.port = 5432
        return create_engine(
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db_name}"
        )


# ──────────────────────────────────────────────
# INSPEKSI DATABASE
# ──────────────────────────────────────────────

def list_tables(engine: Engine) -> List[str]:
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
    inspector = inspect(engine)
    return inspector.get_table_names()


def inspect_table_structure(engine: Engine, table_name: str) -> List[Dict[str, Any]]:
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
    inspector = inspect(engine)

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


def view_table_content(engine: Engine, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
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
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]

    if not columns:
        return []

    # Validasi nama tabel untuk mencegah SQL Injection
    safe_table_name = validate_db_name(table_name)

    with Session(engine) as session:
        query = text(f"SELECT * FROM {safe_table_name} LIMIT :limit")
        rows = session.connection().execute(query, {"limit": limit}).fetchall()

        if not rows:
            return []

        # Konversi setiap row (tuple) menjadi dict {nama_kolom: nilai}
        return [
            {columns[i]: row[i] for i in range(len(columns))}
            for row in rows
        ]


# ──────────────────────────────────────────────
# OPERASI DDL (Struktur Tabel)
# ──────────────────────────────────────────────

def create_dynamic_table(engine: Engine, table_name: str, columns_def: Dict[str, Any]) -> str:
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
    for col_name, col_type in columns_def.items():
        # Kolom 'id' otomatis menjadi Primary Key
        is_pk = col_name.lower() == "id"
        columns.append(Column(col_name, col_type, primary_key=is_pk))

    # Daftarkan tabel ke metadata lalu buat di database fisik
    Table(safe_name, metadata, *columns)
    metadata.create_all(engine)

    return f"Sukses: Tabel '{safe_name}' berhasil dibuat!"


def add_new_column(engine: Engine, table_name: str, column_name: str, column_type: str) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan.")

    # DDL ALTER TABLE - aman selama input berasal dari sistem internal
    query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    with Session(engine) as session:
        session.connection().execute(query)
        session.commit()

    return (
        f"Sukses: Kolom '{column_name}' ({column_type}) "
        f"berhasil ditambahkan ke tabel '{table_name}'."
    )


# ──────────────────────────────────────────────
# OPERASI DML (Isi Data)
# ──────────────────────────────────────────────

def insert_dynamic_data(engine: Engine, table_name: str, data: Dict[str, Any]) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

    target_table = metadata.tables[table_name]

    with Session(engine) as session:
        # insert().values() aman dari SQL Injection karena menggunakan parameterized query
        query = target_table.insert().values(**data)
        session.connection().execute(query)
        session.commit()

    return f"Sukses: Data berhasil ditambahkan ke tabel '{table_name}'."


def update_table_data(engine: Engine, table_name: str, update_values: Dict[str, Any], condition_str: str, condition_params: Dict[str, Any]) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan.")

    # Susun klausa SET: "stok = :stok, harga = :harga"
    set_clauses = [f"{col} = :{col}" for col in update_values.keys()]
    set_str = ", ".join(set_clauses)

    raw_query = f"UPDATE {table_name} SET {set_str} WHERE {condition_str}"
    query = text(raw_query)

    # Gabungkan semua parameter: data update + parameter kondisi WHERE
    bind_params = {**update_values, **condition_params}

    with Session(engine) as session:
        result = session.connection().execute(query, bind_params)
        session.commit()

    return (
        f"Sukses: {result.rowcount} baris data pada tabel "
        f"'{table_name}' berhasil diperbarui."
    )


# ──────────────────────────────────────────────
# OPERASI HAPUS DATA / TABEL
# ──────────────────────────────────────────────

def delete_one_row(engine: Engine, table_name: str, condition_str: str, condition_params: Dict[str, Any]) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

    safe_table_name = validate_db_name(table_name)

    raw_query = f"DELETE FROM {safe_table_name} WHERE {condition_str}"
    query = text(raw_query)

    with Session(engine) as session:
        result = session.connection().execute(query, condition_params)
        session.commit()

    if result.rowcount == 0:
        raise ValueError(
            f"Tidak ada data yang cocok dengan kondisi '{condition_str}' "
            f"di tabel '{table_name}'. Tidak ada baris yang dihapus."
        )

    return (
        f"Sukses: {result.rowcount} baris data dengan kondisi '{condition_str}' "
        f"berhasil dihapus dari tabel '{table_name}'."
    )


def clear_table_data(engine: Engine, table_name: str, db_type: Literal["sqlite", "mysql", "postgresql"]) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

    with Session(engine) as session:
        conn = session.connection()

        if db_type.lower() == "sqlite":
            # SQLite tidak support TRUNCATE, gunakan DELETE FROM
            conn.execute(text(f"DELETE FROM {table_name}"))
            try:
                # Reset counter autoincrement (jika ada)
                conn.execute(
                    text("DELETE FROM sqlite_sequence WHERE name = :tbl"),
                    {"tbl": table_name}
                )
            except Exception:
                pass  # Abaikan jika tabel tidak pakai AUTOINCREMENT
        else:
            # MySQL dan PostgreSQL: TRUNCATE jauh lebih efisien untuk data besar
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))

        session.commit()

    return f"Sukses: Semua data di dalam tabel '{table_name}' berhasil dikosongkan."


def drop_table(engine: Engine, table_name: str) -> str:
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
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise ValueError(f"Tabel '{table_name}' tidak ditemukan di database.")

    # Ambil objek tabel dari metadata hasil refleksi, lalu drop
    target_table = metadata.tables[table_name]
    target_table.drop(bind=engine)

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