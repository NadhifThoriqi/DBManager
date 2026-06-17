# DBManager — Database Studio

DBManager adalah aplikasi web untuk mengelola database secara visual melalui antarmuka mirip studio. Mendukung **SQLite**, **MySQL**, dan **PostgreSQL** dengan backend REST API berbasis FastAPI dan frontend HTML murni.

---

## ✨ Fitur

- 🔐 **Autentikasi** — Sign in / Sign up / Logout via JWT cookie (HTTPOnly)
- 🗄️ **Manajemen Database** — Buat, lihat, dan hapus database (SQLite, MySQL, PostgreSQL)
- 📋 **Manajemen Tabel** — Buat tabel dinamis, tambah kolom, lihat struktur & isi data
- ✏️ **Operasi Data (DML)** — Insert, update, hapus baris, kosongkan tabel, hingga drop tabel
- 🌐 **Frontend Bawaan** — UI dark-mode berbasis HTML + CSS + JS tanpa framework

---

## 🗂️ Struktur Proyek

```
DBManager/
├── back-and/               # Backend (FastAPI)
│   ├── main.py             # Entry point aplikasi
│   ├── requirements.txt    # Dependensi Python
│   ├── .env.example        # Contoh variabel environment
│   └── app/
│       ├── api/            # Definisi endpoint & request/response model
│       │   ├── auth.py
│       │   ├── pydatabase.py
│       │   └── pytable.py
│       └── services/       # Logika bisnis
│           ├── auth.py
│           ├── pydatabase.py
│           └── pytable.py
└── frot-and/               # Frontend
    └── index.html          # UI Database Studio (single file)
```

---

## ⚙️ Instalasi & Menjalankan

### 1. Clone / Ekstrak Proyek

```bash
unzip DBManager.zip
cd DBManager/back-and
```

### 2. Buat Virtual Environment

```bash
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows
```

### 3. Install Dependensi

```bash
pip install -r requirements.txt
```

> Untuk koneksi MySQL, tambahkan `pymysql`. Untuk PostgreSQL, tambahkan `psycopg2-binary`.

### 4. Konfigurasi Environment

Salin `.env.example` menjadi `.env` lalu isi nilainya:

```bash
cp .env.example .env
```

```env
SECRET_KEY = "ganti_dengan_secret_key_yang_kuat"
```

### 5. Jalankan Server

```bash
python main.py
```

Server akan berjalan di `http://0.0.0.0:2606` dengan prefix path `/thorix`.

> Dokumentasi API otomatis tersedia di: `http://localhost:2606/thorix/docs`

### 6. Buka Frontend

Buka file `frot-and/index.html` langsung di browser, lalu arahkan **Base URL** ke server backend.

---

## 🔌 Endpoint API

### Auth — `/auth`

| Method | Path | Keterangan |
|--------|------|------------|
| `POST` | `/auth/signin` | Login & set cookie JWT |
| `POST` | `/auth/signup` | Daftar akun baru |
| `POST` | `/auth/logout` | Hapus cookie / logout |

### Database — `/database`

| Method | Path | Keterangan |
|--------|------|------------|
| `POST` | `/database/create/sqlite` | Buat file database SQLite |
| `POST` | `/database/create/mysql` | Buat database di MySQL |
| `POST` | `/database/create/postgresql` | Buat database di PostgreSQL |
| `GET` | `/database/show/sqlite` | Daftar file `.db` di server |
| `GET` | `/database/show/mysql` | Daftar database MySQL |
| `GET` | `/database/show/postgresql` | Daftar database PostgreSQL |
| `DELETE` | `/database/delete/sqlite` | Hapus file SQLite |
| `DELETE` | `/database/delete/mysql` | Hapus database MySQL |
| `DELETE` | `/database/delete/postgresql` | Hapus database PostgreSQL |

### Tabel — `/table`

| Method | Path | Keterangan |
|--------|------|------------|
| `POST` | `/table/list` | Daftar semua tabel |
| `POST` | `/table/structure` | Struktur kolom tabel |
| `POST` | `/table/content` | Isi data tabel (dengan limit) |
| `POST` | `/table/create` | Buat tabel baru secara dinamis |
| `POST` | `/table/column/add` | Tambah kolom ke tabel |
| `POST` | `/table/insert` | Insert satu baris data |
| `PUT` | `/table/update` | Update data dengan kondisi WHERE |
| `DELETE` | `/table/row` | Hapus baris berdasarkan kondisi |
| `DELETE` | `/table/clear` | Kosongkan semua data tabel |
| `DELETE` | `/table/drop` | Hapus tabel secara permanen ⚠️ |

---

## 🔒 Autentikasi

Sistem menggunakan **JWT** yang disimpan sebagai **HTTPOnly cookie** (`access_token`) dengan masa berlaku 30 hari. Payload token menyimpan informasi kredensial database (`sub`, `pw`, `db`) yang digunakan secara otomatis saat mengakses endpoint yang membutuhkan autentikasi.

---

## 🧰 Teknologi

| Komponen | Teknologi |
|----------|-----------|
| Backend | FastAPI + Uvicorn |
| ORM / Query | SQLAlchemy (via SQLModel) |
| Autentikasi | PyJWT + HTTPOnly Cookie |
| Validasi | Pydantic v2 |
| Frontend | HTML + CSS + Vanilla JS |
| Database | SQLite / MySQL / PostgreSQL |

---

## 📝 Catatan

- Endpoint MySQL & PostgreSQL membutuhkan login terlebih dahulu.
- Endpoint SQLite (create, show, delete dasar) tidak memerlukan autentikasi.
- Konfigurasi `root_path="/thorix"` dirancang untuk dijalankan di balik **Nginx reverse proxy**.
- Ubah `secure=False` menjadi `secure=True` pada cookie jika sudah menggunakan **HTTPS**.
