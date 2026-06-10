# Panduan Eksperimen & Pengujian Sistem Client-Proxy-Server

.Dokumen ini memuat panduan operasional teknis secara menyeluruh untuk mengeksekusi sistem Client-Proxy-Server berbasis *low-level socket programming* menggunakan Python 3. .Seluruh prosedur dikonfigurasikan secara spesifik menggunakan lingkungan editor **Visual Studio Code (VS Code)** dan divalidasi menggunakan **Wireshark Packet Analyzer** .

---

## 1. Arsitektur Komponen Berkas Sistem
.Sistem ini diimplementasikan menggunakan tepat tiga berkas Python utama:
* .**`webserver.py`**: Beroperasi pada port 8000 (TCP untuk HTTP) dan port 9000 (UDP untuk Echo). .Berkas ini berfungsi melayani permintaan berkas HTML statis, menangani kode galat standar (404 Not Found dan 500 Internal Server Error), mencatat log aktivitas secara rinci, serta menerapkan model *multithreading* untuk menangani beberapa koneksi simultan.
* .**`proxy.py`**: Beroperasi pada port 8080 (TCP) sebagai perantara tunggal (*gateway*) antara klien dan server .Berkas ini menjalankan mekanisme *caching* wajib untuk menyimpan respons HTTP secara lokal ke dalam direktori `cache/` berdasarkan jalur URL, mencatat log status Cache HIT atau MISS, serta menangani galat propagasi seperti 502 Bad Gateway dan 504 Gateway Timeout.
* .**`client.py`**: Berfungsi sebagai alat pengujian fungsionalitas ganda.*Mode TCP* digunakan untuk mengirimkan permintaan HTTP GET ke Proxy Server lalu menampilkan teks HTML mentah pada terminal.*Mode UDP* digunakan khusus untuk melakukan pengujian performa kualitas jaringan (QoS) dengan mengirimkan minimal 10 paket proaktif terstruktur langsung ke Web Server dengan batas waktu tunggu (*timeout*) maksimal 1 detik per paket.*Mode Multi Client* digunakan untuk meluncurkan 5 *instance* klien TCP secara simultan guna memvalidasi keandalan model *thread-per-connection* pada server dan proxy .

---

## 2. Panduan Menjalankan Sistem di VS Code

### Langkah 2.1: Menyiapkan Workspace Proyek
1. .Buka aplikasi **VS Code** pada perangkat komputer Anda.
2. .Pilih menu `File` > `Open Folder...`, lalu arahkan ke direktori proyek tempat tiga berkas Python di atas dan aset berkas `index.html` diletakkan dalam satu folder root yang sama.
3. Buka terminal terintegrasi dengan menekan kombinasi tombol `Ctrl + \`` atau melalui menu `Terminal` > `New Terminal`.

### Langkah 2.2: Mengonfigurasi Pembagian Panel Terminal (Split Terminal)
Karena komponen server dan proxy berjalan secara persisten menggunakan kalang tak berujung (`while True`), terminal harus dibagi menjadi beberapa panel agar aktivitas log dapat dipantau berdampingan secara *real-time*:
1. Pada panel terminal terintegrasi VS Code yang sudah terbuka, perhatikan pojok kanan atas area terminal lalu klik ikon **Split Terminal** (ikon kotak terbagi dua) atau gunakan kombinasi tombol `Ctrl + Shift + 5`.
2. Lakukan klik sebanyak dua kali lagi hingga terminal terbagi menjadi minimal **3 panel berdampingan**.
3. Sesuaikan lebar masing-masing panel agar pembacaan teks baris log tidak terpotong.

### Langkah 2.3: Inisialisasi Berurutan Komponen Jaringan
.Inisialisasi eksekusi program wajib mengikuti urutan hierarki topologi dari sisi belakang menuju sisi depan untuk mencegah kegagalan pengikatan koneksi (*Connection Refused*):

* **Terminal 1 (Panel Paling Kiri) - Menjalankan Web Server:**
    ```bash
    python webserver.py
    ```
    *Pastikan terminal ini tetap dibiarkan aktif. .Server akan mencetak log startup dan pool thread siap melayani data masuk[cite: 380].*

* **Terminal 2 (Panel Tengah) - Menjalankan Proxy Server:**
    ```bash
    python proxy.py
    ```
    .*Proxy akan mulai mendengarkan koneksi pada port 8080 dan secara otomatis mendeteksi atau membuat folder direktori lokal bernama `cache/`.*

* **Terminal 3 (Panel Paling Kanan) - Menjalankan Klien Tester:**
    *Gunakan panel terminal ke-3 ini untuk mengeksekusi seluruh skenario pengujian fungsional di bawah.*

---

## 3. Skenario Pengujian & Pengumpulan Data Metrik

### Skenario A: Verifikasi Mekanisme TCP Caching (HIT vs MISS)
1. .Pada Terminal 3, jalankan pengujian TCP klien untuk pertama kalinya:
   ```bash
   python client.py
   ```
   Lalu pilih opsi `1` untuk menjalankan TCP.
