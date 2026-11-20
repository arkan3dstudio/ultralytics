# Robot Tracking — Tahap 1 dan 2

Tracking orang yang dipilih lewat kamera, dengan simulasi perintah gerak dan empat roda mecanum.
Skrip ini melanjutkan `project_02_tracking.py` yang sudah ada, dalam worktree `robot_tracking` pada branch
`feat/robot-tracking-sim`. YOLO, ByteTrack, OpenCV, dan virtualenv proyek digunakan kembali; tidak ada dependensi baru.

## Jalankan

Dari folder `yolo` di PowerShell:

```powershell
& ".\robot_tracking\RUN_ROBOT_TRACKING.cmd"
```

Atau panggil Python secara langsung:

```powershell
& ".\.venv\Scripts\python.exe" -B ".\robot_tracking\project_02_tracking.py"
```

Kamera lain atau video lokal dapat dipakai sebagai sumber:

```powershell
& ".\robot_tracking\RUN_ROBOT_TRACKING.cmd" --source 1
& ".\robot_tracking\RUN_ROBOT_TRACKING.cmd" --source ".\videos\people1.mp4"
```

Bobot `yolo26n.pt` dicari di folder skrip lalu folder induknya. Gunakan `--model PATH` untuk bobot lokal lain.
Default target adalah orang (`--class-id 0`); contoh `--class-id 39` memilih botol pada model COCO.
Laptop memakai GPU CUDA jika tersedia, dengan CPU sebagai pilihan otomatis berikutnya.

## Cara mencoba

1. Hadapkan kamera ke orang yang akan diikuti. Klik di dalam kotak deteksinya.
2. Ukuran target saat diklik menjadi acuan posisi maju/mundur. Pindahkan orang lebih jauh atau lebih dekat untuk
   melihat perintah MAJU/MUNDUR. Ini acuan ukuran gambar, belum jarak dalam meter.
3. Gerakkan orang ke kiri/kanan gambar untuk melihat perintah geser samping. Tekan **M** untuk mengganti koreksi
   horizontal menjadi putaran badan robot.
4. Masuknya target ke area tengah dan toleransi ukuran membuat perintah menjadi nol. Target yang tidak teramati pada
   frame saat ini juga menghasilkan nol; skrip tidak memilih ID lain secara otomatis.

| Kontrol                 | Fungsi                                                            |
| ----------------------- | ----------------------------------------------------------------- |
| Klik kiri               | Pilih target dan tetapkan acuan ukuran baru                       |
| Space                   | Jeda/lanjut perintah simulasi; kamera dan tracking tetap berjalan |
| R                       | Jadikan ukuran target saat ini sebagai acuan maju/mundur          |
| C                       | Lepas target dan hentikan perintah                                |
| M                       | Ganti mode geser samping / putar badan                            |
| S                       | Simpan screenshot ke `robot_tracking/runs/robot_tracking/`        |
| Q / Esc / tutup jendela | Keluar dan lepaskan kamera                                        |

## Membaca simulasi

- FL/FR adalah roda depan kiri/kanan; RL/RR adalah belakang kiri/kanan, dilihat dari arah hadap robot.
- Susunan mecanum memakai roller membentuk X dilihat dari atas. Nilai positif berarti putaran roda untuk maju.
- Keluaran roda adalah nilai relatif dengan batas ±60%; nilai tersebut belum merupakan PWM, RPM, atau m/s.
- Sumbu positif: maju, geser kiri, dan putar kiri. Saat target berada di kanan gambar, koreksinya geser/putar kanan.
- Keempat roda dinormalisasi bersama agar perbandingan geraknya dipertahankan.
- Toleransi horizontal adalah ±5% lebar gambar dari tengah. Toleransi ukuran adalah ±12% dari acuan tinggi target.

Pemetaan roda mengikuti [kinematika mecanum](https://docs.wpilib.org/en/stable/docs/software/kinematics-and-odometry/mecanum-drive-kinematics.html).
Rumus relatifnya, dalam urutan FL/FR/RL/RR, adalah `f-l-w`, `f+l+w`, `f+l-w`, `f-l+w`.

Perubahan pose, target terpotong tepi gambar, dan penutupan tubuh dapat mengubah tinggi kotak tanpa perubahan jarak.
ByteTrack juga dapat menukar ID saat orang saling menutupi. Jika target memperoleh ID baru, pilih ulang dengan klik.
Pemulihan ID yang sama melanjutkan simulasi saat target terlihat lagi. Pada tahap ini acuan ukuran belum menggantikan
sensor jarak, dan belum ada sambungan ke mikrokontroler atau pengiriman perintah ke motor.

Program ini menyimulasikan keluaran pengendali dari gambar kamera. Kamera pada laptop tetap diam; perubahan hasil
akibat gerakan robot sebenarnya belum disimulasikan sebagai model fisika.
