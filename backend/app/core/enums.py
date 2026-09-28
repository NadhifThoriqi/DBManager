from enum import StrEnum

class Indeks(StrEnum):
    NONE = ""               # isi NONE jika tidak index
    PRIMARY = "primary"     # Indeks utama, tidak boleh kembar, dan tidak boleh kosong (NOT NULL).
    UNIQUE = "unique"       # Data tidak boleh kembar, tetapi boleh berisi nilai kosong (NULL).
    INDEX = "index"         # Indeks biasa untuk mempercepat pencarian data yang nilainya boleh kembar.
    FULLTEXT = "fulltext"   # Indeks khusus untuk mencari teks panjang (seperti isi artikel atau berita).
    SPATIAL = "spatial"     # Indeks khusus untuk data geografis atau koordinat (peta).
