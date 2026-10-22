# 🏠 Rental House Management & WhatsApp Gateway Module (Odoo 18)

![Odoo Version](https://img.shields.io/badge/Odoo-18.0-714B67?style=flat&logo=odoo)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=flat&logo=postgresql)
![Status](https://img.shields.io/badge/Status-Completed-success)

Modul custom Odoo 18 yang dirancang khusus untuk mengelola unit rumah sewa, memantau kontrak dan cicilan penyewa, otomatisasi notifikasi pengingat via **WhatsApp Gateway (Fonnte API)**, manajemen pencatatan kas masuk otomatis, hingga pembatalan/penyelesaian kontrak sewa.

---

## 📸 Galeri Antarmuka & Tangkapan Layar (Screenshots)

### 1. Pemantauan Sewa & Master Data Unit
| Pemantauan Sewa (Kanban Grid View) | Master Unit Rumah (Status Available/Rented) |
| <img width="956" height="435" alt="image" src="https://github.com/user-attachments/assets/147b1051-491e-4c5a-a7c8-41b414573bee" />
 | <img width="956" height="445" alt="image" src="https://github.com/user-attachments/assets/333c9109-ff4b-4290-9872-4c320a529a0a" />
|

---

### 2. Form Kontrak & Integrasi WhatsApp Gateway
| Form Detail Kontrak & Tombol Aksi | Riwayat Pengiriman Pesan WA (Log) |
|<img width="917" height="425" alt="image" src="https://github.com/user-attachments/assets/6e6b65a6-50d2-4c40-b9ad-d02590c99abc" />
 |<img width="949" height="445" alt="image" src="https://github.com/user-attachments/assets/251445b9-9cf1-42b5-a9a4-217d8c2e19d7" />
|

---

### 3. Pembukuan Keuangan & Laporan PDF
| Pembukuan Keuangan Kas Masuk | Cetak Kuitansi / Laporan PDF |
|<img width="956" height="437" alt="image" src="https://github.com/user-attachments/assets/58eb0e0d-4f56-480e-9d08-f020230886e5" />
| <img width="934" height="488" alt="image" src="https://github.com/user-attachments/assets/3f61a344-10b9-45ea-9fc2-8b3782e17759" />
 |

---

## 🌟 Fitur Utama

- **Master Unit Rumah (`rental.house`)**: Manajemen status ketersediaan unit sewa (`Tersedia (Kosong)` vs `Tersewa`).
- **Pemantauan Kontrak (`rental.contract`)**: 
  - Tampilan visual Kanban Grid horizontal yang responsif.
  - Penomoran otomatis berurutan (*Auto-Sequence*).
  - Validasi ketat pencegahan *double-booking* pada rumah yang sedang ditempati.
  - Fitur **Putus / Selesai Kontrak** yang otomatis mengembalikan status rumah menjadi *Tersedia*.
- **Otomatisasi WhatsApp Gateway (Fonnte API)**:
  - **Pesan Manual**: Tombol Cepat pemicu tagihan langsung ke nomor penyewa.
  - **Cron Job Harian**: Pengingat otomatis H-5 sebelum jatuh tempo dan Peringatan H+1 keterlambatan.
  - **Log Komunikasi**: Pencatatan riwayat pengiriman pesan (Terkirim / Gagal).
- **Pembukuan Keuangan (`rental.accounting`)**: Auto-generate pencatatan kas masuk saat tagihan dikonfirmasi lunas.
- **Pelaporan PDF QWeb Multi-Halaman**: Cetak kuitansi resmi penyewa dan lampiran arsip pengelola dengan pembatas halaman (*pagebreak*).

---

## 🛠️ Teknologi & Tools

- **Core Framework**: Odoo 18.0 Community Edition
- **Language**: Python 3.10+, XML, QWeb
- **Database**: PostgreSQL
- **Integration**: Fonnte REST API (WhatsApp Gateway)
- **UI/UX Framework**: Bootstrap 5 Badge & Grid System

---

## 📂 Struktur Modul

```text
rental_house_management/
├── data/
│   └── rental_sequence.xml        # Konfigurasi penomoran otomatis
├── docs/
│   └── images/                    # Asset gambar untuk portofolio README
│       ├── kanban_view.png
│       ├── form_view.png
│       ├── master_house.png
│       ├── accounting_view.png
│       ├── pdf_report.png
│       └── wa_log.png
├── models/
│   ├── __init__.py
│   └── rental_contract.py         # Business Logic, REST API WA, & Cron Job
├── security/
│   └── ir.model.access.csv        # Pengaturan Hak Akses (Access Rights)
├── views/
│   ├── rental_contract_view.xml   # Form, List, Kanban, Search View, & Menus
│   └── rental_report_template.xml # Template Kuitansi PDF QWeb
├── __init__.py
├── __manifest__.py                # Metadata Modul
└── README.md                      # Dokumentasi Proyek
