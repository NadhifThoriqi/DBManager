"""
=============
pydatabase.py
=============
Modul utilitas untuk manajemen DATABASE (bukan tabel) di level tertinggi:
membuat, menampilkan daftar, dan menghapus database.

Mendukung tiga jenis database:
    - SQLite     : berbasis file .db, tanpa server
    - MySQL      : menggunakan driver pymysql
    - PostgreSQL : menggunakan driver psycopg2

Dependensi:
    pip install sqlalchemy pymysql psycopg2-binary

Struktur Modul:
    - validate_db_name   : Validasi nama database (anti SQL Injection)
    - _build_url         : Helper membangun URL koneksi SQLAlchemy    
    - close_connection   : Decorator otomatis tutup koneksi setelah eksekusi
    - Create             : Kelas untuk membuat database baru
    - Show               : Kelas untuk menampilkan daftar database yang ada
    - Delete             : Kelas untuk menghapus database
"""

from typing import Any, Callable, List, Tuple, Optional
import os
import re

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import ProgrammingError
except ImportError:
    raise ImportError(
        "sqlalchemy belum terinstall. "
        "Install dengan: pip install sqlalchemy pymysql psycopg2-binary"
    )


# ──────────────────────────────────────────────
# KONSTANTA: DATABASE SISTEM YANG DILINDUNGI
# ──────────────────────────────────────────────

# Database bawaan MySQL yang tidak boleh dihapus
_PROTECTED_MYSQL_DBS = {"information_schema", "mysql", "performance_schema", "sys"}

# Database bawaan PostgreSQL yang tidak boleh dihapus
_PROTECTED_PG_DBS = {"postgres", "template0", "template1"}


# ──────────────────────────────────────────────
# FUNGSI UTILITAS
# ──────────────────────────────────────────────

def validate_db_name(name: str) -> str:
    """
    Validasi nama database atau tabel agar hanya mengandung karakter aman.
    Mencegah SQL Injection pada bagian identifier (nama tabel/db).

    Aturan: hanya huruf (a-z, A-Z), angka (0-9), dan underscore (_).

    Parameters
    ----------
    name : str - nama database atau tabel yang akan divalidasi

    Returns
    -------
    str - nama yang sudah tervalidasi (dikembalikan apa adanya jika valid)

    Raises
    ------
    ValueError - jika nama mengandung karakter tidak valid

    Contoh penggunaan:
    ------------------
    validate_db_name("toko_db")       # ✅ → "toko_db"
    validate_db_name("TokoV2")        # ✅ → "TokoV2"
    validate_db_name("toko-db")       # ❌ raises ValueError (ada tanda -)
    validate_db_name("toko db")       # ❌ raises ValueError (ada spasi)
    validate_db_name("'; DROP TABLE") # ❌ raises ValueError (SQL Injection)
    """
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError(f"Nama database tidak valid: '{name}'. Hanya huruf, angka, dan underscore yang diperbolehkan.")
    return name


def _build_url(dialect: str, host: str, user: str, password: str, port: Optional[int], database: str = "") -> str:
    """
    Helper internal: membangun string URL koneksi SQLAlchemy.

    Parameters
    ----------
    dialect  : str          - jenis driver, misal: 'mysql+pymysql', 'postgresql+psycopg2'
    host     : str          - alamat server database
    user     : str          - username database
    password : str          - password database
    port     : Optional[int]- nomor port (None = tidak disertakan di URL)
    database : str          - nama database tujuan (opsional, default kosong)

    Returns
    -------
    str - URL koneksi SQLAlchemy yang siap digunakan

    Contoh output:
    --------------
    _build_url("mysql+pymysql", "localhost", "root", "secret", 3306, "toko_db")
    → "mysql+pymysql://root:secret@localhost:3306/toko_db"

    _build_url("postgresql+psycopg2", "localhost", "postgres", "pass", 5432)
    → "postgresql+psycopg2://postgres:pass@localhost:5432"
    """
    port_str = f":{port}" if port else ""
    db_str = f"/{database}" if database else ""
    return f"{dialect}://{user}:{password}@{host}{port_str}{db_str}"


def close_connection(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator: otomatis menutup koneksi database setelah fungsi selesai,
    baik sukses maupun terjadi error (via blok finally).

    Fungsi yang didekorasi harus mengembalikan Tuple (result, conn),
    di mana conn adalah objek koneksi SQLAlchemy yang akan di-close.

    Contoh fungsi yang cocok didekorasi:
    -------------------------------------
    @close_connection
    def mysql(self) -> Tuple[str, Any]:
        conn = engine.connect()
        conn.execute(...)
        return "pesan sukses", conn   # ← conn akan di-close otomatis
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = conn = None
        try:
            result, conn = func(*args, **kwargs)
            return result
        except Exception:
            raise  # Teruskan exception ke pemanggil
        finally:
            # Tutup koneksi apapun yang terjadi
            if conn and hasattr(conn, 'close'):
                conn.close()
    return wrapper


# ──────────────────────────────────────────────
# CLASS: CREATE DATABASE
# ──────────────────────────────────────────────

class Create:
    """
    Kelas untuk membuat database baru.

    Mendukung: SQLite, MySQL, PostgreSQL.

    Contoh penggunaan:
    ------------------
    # SQLite (tidak butuh host/user/password)
    creator = Create(db_name="toko")
    print(creator.sqlite())

    # MySQL
    creator = Create(db_name="toko_db", user="root", password="secret", port=3306)
    print(creator.mysql())

    # PostgreSQL
    creator = Create(db_name="toko_db", user="postgres", password="secret", port=5432)
    print(creator.postgresql())
    """

    def __init__(self, db_name: str, user: Optional[str] = 'root', password: Optional[str] = '', host: Optional[str] = 'localhost', port: Optional[int] = None,) -> None:
        """
        Parameters
        ----------
        db_name  : str          - nama database yang akan dibuat
        user     : str          - username (default: 'root')
        password : str          - password (default: kosong)
        host     : str          - alamat server (default: 'localhost')
        port     : Optional[int]- nomor port (MySQL: 3306, PostgreSQL: 5432)
        """
        self.user = user or 'root'
        self.password = password or ''
        self.host = host or 'localhost'
        self.port = port
        self.db_name = validate_db_name(db_name)  # Validasi sebelum disimpan

    def sqlite(self) -> str:
        """
        Buat database SQLite berupa file .db di direktori saat ini.
        Jika file sudah ada, koneksi tetap berhasil (tidak error, tidak overwrite).

        Returns
        -------
        str - pesan sukses

        Contoh:
        -------
        Create(db_name="inventaris").sqlite()
        # Membuat file: inventaris.db
        # Output: "Database SQLite 'inventaris.db' berhasil dibuat/dihubungkan."
        """
        try:
            engine = create_engine(f"sqlite:///{self.db_name}.db")
            # Membuka koneksi memicu pembuatan file .db secara fisik
            with engine.connect():
                pass
            return f"Database SQLite '{self.db_name}.db' berhasil dibuat/dihubungkan."
        except Exception as e:
            raise ValueError(f"Gagal membuat database SQLite: {e}") from e

    @close_connection
    def mysql(self) -> Tuple[str, Any]:
        """
        Buat database MySQL. Menggunakan CREATE DATABASE IF NOT EXISTS,
        sehingga aman dijalankan berulang kali.

        Returns
        -------
        str - pesan sukses (koneksi di-close otomatis oleh decorator)

        Contoh:
        -------
        Create(db_name="toko_db", user="root", password="rahasia", port=3306).mysql()
        # Output: "Database MySQL 'toko_db' berhasil dibuat."
        """
        conn = None
        if not self.port:
            self.port = 3360
        try:
            # Koneksi ke MySQL server TANPA menentukan database dulu
            url = _build_url("mysql+pymysql", self.host, self.user, self.password, self.port)
            engine = create_engine(url)
            conn = engine.connect()
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.db_name}"))
            return f"Database MySQL '{self.db_name}' berhasil dibuat.", conn
        except Exception as e:
            raise ValueError(f"Gagal membuat database MySQL: {e}") from e

    @close_connection
    def postgresql(self) -> Tuple[str, Any]:
        """
        Buat database PostgreSQL.
        Terhubung ke database 'postgres' (default system db) terlebih dahulu,
        lalu membuat database baru dari sana.

        Returns
        -------
        str - pesan sukses atau info bahwa database sudah ada

        Contoh:
        -------
        Create(db_name="toko_db", user="postgres", password="rahasia", port=5432).postgresql()
        # Output: "Database PostgreSQL 'toko_db' berhasil dibuat."
        # Jika sudah ada: "Database PostgreSQL 'toko_db' sudah ada."
        """
        conn = None
        if not self.port:
            self.port = 5432
        try:
            # AUTOCOMMIT diperlukan karena CREATE DATABASE tidak bisa dijalankan di dalam transaksi
            url = _build_url("postgresql+psycopg2", self.host, self.user, self.password, self.port, "postgres")
            engine = create_engine(url, isolation_level="AUTOCOMMIT")
            conn = engine.connect()
            try:
                conn.execute(text(f"CREATE DATABASE {self.db_name}"))
                return f"Database PostgreSQL '{self.db_name}' berhasil dibuat.", conn
            except ProgrammingError:
                # ProgrammingError muncul jika database sudah ada → bukan error fatal
                return f"Database PostgreSQL '{self.db_name}' sudah ada.", conn
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Gagal membuat database PostgreSQL: {e}") from e


# ──────────────────────────────────────────────
# CLASS: SHOW DATABASE
# ──────────────────────────────────────────────

class Show:
    """
    Kelas untuk menampilkan daftar database yang ada di server.

    Contoh penggunaan:
    ------------------
    # SQLite: cari semua file .db di folder tertentu
    show = Show()
    jumlah, daftar = show.sqlite(search_dir="./data")

    # MySQL
    show = Show(user="root", password="secret", port=3306)
    jumlah, daftar = show.mysql()

    # PostgreSQL
    show = Show(user="postgres", password="secret", port=5432)
    jumlah, daftar = show.postgresql()
    """

    def __init__(self, user: Optional[str] = 'root', password: Optional[str] = '', host: Optional[str] = 'localhost', port: Optional[int] = None,) -> None:
        """
        Parameters
        ----------
        user     : str          - username database
        password : str          - password database
        host     : str          - alamat server (default: 'localhost')
        port     : Optional[int]- MySQL: 3306 | PostgreSQL: 5432
        """
        self.host = host or 'localhost'
        self.user = user or 'root'
        self.password = password or ''
        self.port = port

    def sqlite(self, search_dir: str = ".") -> Tuple[int, List[Tuple[str, str, int]]]:
        """
        Temukan semua file SQLite (.db) dalam direktori yang ditentukan.

        Parameters
        ----------
        search_dir : str - direktori yang akan dicari (default: direktori saat ini '.')

        Returns
        -------
        Tuple[int, List[Tuple[str, str, int]]]
            - int                     : jumlah file .db yang ditemukan
            - List[Tuple[str,str,int]]: list berisi (nama_file, path_lengkap, ukuran_byte)

        Contoh:
        -------
        show = Show()
        jumlah, daftar = show.sqlite(search_dir="./data")
        print(jumlah)   # 2
        print(daftar)
        # [
        #   ('toko.db', './data/toko.db', 32768),
        #   ('inventaris.db', './data/inventaris.db', 16384)
        # ]
        """
        try:
            db_files: List[str] = [
                f for f in os.listdir(search_dir)
                if f.endswith('.db') and os.path.isfile(os.path.join(search_dir, f))
            ]
            result: List[Tuple[str, str, int]] = [
                (
                    f,
                    os.path.join(search_dir, f),
                    os.path.getsize(os.path.join(search_dir, f))
                )
                for f in db_files
            ]
            return (len(result), result)
        except Exception as e:
            raise ValueError(f"Error mencari file SQLite: {e}") from e

    @close_connection
    def mysql(self) -> Tuple[Any, Any]:
        """
        Ambil daftar semua database di server MySQL (termasuk sistem database).

        Returns
        -------
        Tuple[int, List[str]]
            - int       : jumlah database
            - List[str] : nama-nama database

        Contoh:
        -------
        show = Show(user="root", password="rahasia", port=3306)
        jumlah, daftar = show.mysql()
        print(jumlah)  # 5
        print(daftar)  # ['information_schema', 'mysql', 'performance_schema', 'sys', 'toko_db']
        """
        conn = None
        if not self.port:
            self.port = 3360
        try:
            url = _build_url("mysql+pymysql", self.host, self.user, self.password, self.port)
            engine = create_engine(url)
            conn = engine.connect()
            rows = [row[0] for row in conn.execute(text("SHOW DATABASES")).fetchall()]
            return (len(rows), rows), conn
        except Exception as e:
            raise ValueError(f"Gagal mengambil daftar database MySQL: {e}") from e

    @close_connection
    def postgresql(self) -> Tuple[Tuple[int, Any], Any]:
        """
        Ambil daftar database di PostgreSQL (hanya database non-template).

        Returns
        -------
        Tuple[int, List[str]]
            - int       : jumlah database
            - List[str] : nama-nama database

        Contoh:
        -------
        show = Show(user="postgres", password="rahasia", port=5432)
        jumlah, daftar = show.postgresql()
        print(jumlah)  # 3
        print(daftar)  # ['postgres', 'toko_db', 'hr_db']
        """
        conn = None
        if not self.port:
            self.port = 5432
        try:
            url = _build_url("postgresql+psycopg2", self.host, self.user, self.password, self.port, "postgres")
            engine = create_engine(url)
            conn = engine.connect()
            # Hanya ambil database bukan template (template0 & template1 disembunyikan)
            rows = [
                row[0] for row in conn.execute(
                    text("SELECT datname FROM pg_database WHERE datistemplate = false;")
                ).fetchall()
            ]
            return (len(rows), rows), conn
        except Exception as e:
            raise ValueError(f"Gagal mengambil daftar database PostgreSQL: {e}") from e


# ──────────────────────────────────────────────
# CLASS: DELETE DATABASE
# ──────────────────────────────────────────────

class Delete:
    """
    Kelas untuk menghapus database secara permanen.

    ⚠️  Operasi ini TIDAK DAPAT DIBATALKAN!
        Database sistem yang dilindungi tidak bisa dihapus.

    Database yang dilindungi:
        MySQL      : information_schema, mysql, performance_schema, sys
        PostgreSQL : postgres, template0, template1

    Contoh penggunaan:
    ------------------
    # SQLite
    Delete(db_name="toko").sqlite()

    # MySQL
    Delete(db_name="toko_db", user="root", password="secret", port=3306).mysql()

    # PostgreSQL
    Delete(db_name="toko_db", user="postgres", password="secret", port=5432).postgresql()
    """

    def __init__(self, db_name: str, user: Optional[str] = 'root', password: Optional[str] = '', host: Optional[str] = 'localhost', port: Optional[int] = None) -> None:
        """
        Parameters
        ----------
        db_name  : str          - nama database yang akan dihapus
        user     : str          - username database
        password : str          - password database
        host     : str          - alamat server (default: 'localhost')
        port     : Optional[int]- MySQL: 3306 | PostgreSQL: 5432
        """
        self.db_name = validate_db_name(db_name)
        self.host = host or 'localhost'
        self.user = user or 'root'
        self.password = password or ''
        self.port = port

    def sqlite(self) -> str:
        """
        Hapus file database SQLite (.db) dari sistem file.

        Returns
        -------
        str - pesan sukses atau info bahwa file tidak ditemukan

        Raises
        ------
        ValueError - jika file sedang digunakan program lain (PermissionError)

        Contoh:
        -------
        Delete(db_name="toko").sqlite()
        # Menghapus file: toko.db
        # Output: "Database SQLite (File: 'toko') berhasil dihapus."

        Delete(db_name="tidak_ada").sqlite()
        # Output: "File database 'tidak_ada' tidak ditemukan."
        """
        try:
            file_path = f"{self.db_name}.db"
            if os.path.exists(file_path):
                os.remove(file_path)
                return f"Database SQLite (File: '{self.db_name}') berhasil dihapus."
            else:
                return f"File database '{self.db_name}' tidak ditemukan."
        except PermissionError as e:
            raise ValueError(
                "Gagal menghapus! File sedang digunakan oleh program lain. "
                "Pastikan semua koneksi sudah di-close terlebih dahulu."
            ) from e
        except Exception as e:
            raise ValueError(f"Gagal menghapus database: {e}") from e

    @close_connection
    def mysql(self) -> Tuple[str, Any]:
        """
        Hapus database MySQL menggunakan DROP DATABASE IF EXISTS.
        Database sistem yang terdaftar di _PROTECTED_MYSQL_DBS tidak bisa dihapus.

        Returns
        -------
        str - pesan sukses

        Raises
        ------
        ValueError - jika mencoba menghapus database sistem

        Contoh:
        -------
        Delete(db_name="toko_db", user="root", password="rahasia", port=3306).mysql()
        # Output: "Database MySQL 'toko_db' berhasil dihapus."

        Delete(db_name="mysql", user="root", password="rahasia", port=3306).mysql()
        # ❌ raises ValueError: "Database 'mysql' adalah sistem database dan tidak boleh dihapus."
        """
        conn = None
        if not self.port:
            self.port = 3360
        try:
            # Cek proteksi sebelum melakukan apapun ke server
            if self.db_name in _PROTECTED_MYSQL_DBS:
                raise ValueError(
                    f"Database '{self.db_name}' adalah sistem database dan tidak boleh dihapus."
                )

            url = _build_url("mysql+pymysql", self.host, self.user, self.password, self.port)
            engine = create_engine(url)
            conn = engine.connect()
            conn.execute(text(f"DROP DATABASE IF EXISTS {self.db_name}"))
            return f"Database MySQL '{self.db_name}' berhasil dihapus.", conn
        except ValueError:
            raise  # Re-raise ValueError (proteksi) tanpa membungkusnya lagi
        except Exception as e:
            raise ValueError(f"Gagal menghapus database: {e}") from e

    @close_connection
    def postgresql(self) -> Tuple[str, Any]:
        """
        Hapus database PostgreSQL.
        Menggunakan WITH (FORCE) untuk memutus koneksi aktif sebelum drop (PostgreSQL 13+).
        Database sistem yang terdaftar di _PROTECTED_PG_DBS tidak bisa dihapus.

        Returns
        -------
        str - pesan sukses

        Raises
        ------
        ValueError - jika mencoba menghapus database sistem

        Contoh:
        -------
        Delete(db_name="toko_db", user="postgres", password="rahasia", port=5432).postgresql()
        # Output: "Database PostgreSQL 'toko_db' berhasil dihapus."

        Delete(db_name="template0", user="postgres", password="rahasia", port=5432).postgresql()
        # ❌ raises ValueError: "Database 'template0' adalah sistem database dan tidak boleh dihapus."
        """
        conn = None
        if not self.port:
            self.port = 5432
        try:
            # Cek proteksi sebelum melakukan apapun ke server
            if self.db_name in _PROTECTED_PG_DBS:
                raise ValueError(
                    f"Database '{self.db_name}' adalah sistem database dan tidak boleh dihapus."
                )

            # AUTOCOMMIT diperlukan karena DROP DATABASE tidak bisa dalam transaksi
            url = _build_url("postgresql+psycopg2", self.host, self.user, self.password, self.port, "postgres")
            engine = create_engine(url, isolation_level="AUTOCOMMIT")
            conn = engine.connect()
            # WITH (FORCE): putus paksa koneksi aktif ke DB ini sebelum drop (PG 13+)
            conn.execute(text(f"DROP DATABASE IF EXISTS {self.db_name} WITH (FORCE)"))
            return f"Database PostgreSQL '{self.db_name}' berhasil dihapus.", conn
        except ValueError:
            raise  # Re-raise ValueError (proteksi) tanpa membungkusnya lagi
        except Exception as e:
            raise ValueError(f"Gagal menghapus database: {e}") from e


# ──────────────────────────────────────────────
# CONTOH PENGGUNAAN LENGKAP
# ──────────────────────────────────────────────
"""
if __name__ == "__main__":
    from typing import Dict

    # ── SQLite (tidak perlu server) ───────────────
    print("=== SQLite ===")

    # Buat database
    creator = Create(db_name="toko")
    print(creator.sqlite())
    # Output: "Database SQLite 'toko.db' berhasil dibuat/dihubungkan."

    # Tampilkan daftar file .db di folder saat ini
    show = Show()
    jumlah, daftar = show.sqlite(search_dir=".")
    print(f"Ditemukan {jumlah} file SQLite:")
    for nama, path, ukuran in daftar:
        print(f"  {nama} | {path} | {ukuran} bytes")

    # Hapus database
    print(Delete(db_name="toko").sqlite())
    # Output: "Database SQLite (File: 'toko') berhasil dihapus."

    # ── MySQL ─────────────────────────────────────
    print("\n=== MySQL ===")

    MYSQL_CFG: Dict[str, Any] = dict(user="root", password="rahasia", host="localhost", port=3306)

    print(Create(db_name="toko_db", **MYSQL_CFG).mysql())
    # Output: "Database MySQL 'toko_db' berhasil dibuat."

    jumlah, daftar = Show(**MYSQL_CFG).mysql()
    print(f"Total database MySQL: {jumlah}")
    print("Daftar:", daftar)

    print(Delete(db_name="toko_db", **MYSQL_CFG).mysql())
    # Output: "Database MySQL 'toko_db' berhasil dihapus."

    # ── PostgreSQL ────────────────────────────────
    print("\n=== PostgreSQL ===")

    PG_CFG: Dict[str, Any] = dict(user="postgres", password="rahasia", host="localhost", port=5432)

    print(Create(db_name="toko_db", **PG_CFG).postgresql())
    # Output: "Database PostgreSQL 'toko_db' berhasil dibuat."

    jumlah, daftar = Show(**PG_CFG).postgresql()
    print(f"Total database PostgreSQL: {jumlah}")
    print("Daftar:", daftar)

    print(Delete(db_name="toko_db", **PG_CFG).postgresql())
    # Output: "Database PostgreSQL 'toko_db' berhasil dihapus."

    # ── Contoh validasi nama ──────────────────────
    print("\n=== Validasi ===")
    try:
        validate_db_name("toko-db")  # ❌ ada tanda -
    except ValueError as e:
        print(f"Validasi gagal: {e}")

    try:
        Delete(db_name="mysql", **MYSQL_CFG).mysql()  # ❌ database sistem
    except ValueError as e:
        print(f"Proteksi aktif: {e}")
"""