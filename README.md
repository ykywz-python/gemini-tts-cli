# Gemini TTS CLI 🗣️

Generator Text-to-Speech (TTS) via command-line yang menggunakan model `gemini-2.5-flash-preview-tts` dari Google. Didesain untuk menangani teks panjang dengan fitur-fitur canggih seperti rotasi API key, *smart chunking*, dan penggabungan audio otomatis untuk mengatasi limitasi API.

## Cara Penggunaan

`pastikan file key.txt dan prompt.txt sudah dibuat`

Gunakan perintah dasar berikut untuk menjalankan program.

```cmd
# contoh untuk dipowershell
gtts-cli `
-p prompt.txt `
-v Puck `
-o Malam_Abadi `
-k key.txt `
-t 0.7 `
-r 3 `
-d 10 `
--max_chars 4000 `
--no-delete


# Contoh untuk di cmd
gtts-cli ^
-p prompt.txt ^
-v Puck ^
-o Audio_Saya ^
-k key.txt ^
-t 0.5 ^
-r 3 ^
-d 10 ^
--max_chars 4000 ^
--no-delete

```


## Parameter Lengkap

Program ini mendukung berbagai parameter untuk kontrol yang lebih mendalam, mulai dari manajemen API hingga konfigurasi audio.

| **Parameter Panjang** | **Alias** | **Deskripsi** | **Wajib** | **Nilai/Contoh** |
| :--- | :--- | :--- | :---: | :--- |
| **`--prompt`** | `-p` | **Teks input atau jalur ke file `.txt`** yang berisi narasi. | Ya | `"Teks..."` atau `script.txt` |
| **`--output_name`** | `-o` | **Nama dasar untuk file output**. File akhir akan diberi nama `final_[nama_output].wav`. | Tidak | `audio_saya` |
| **`--voice`** | `-v` | **Nama model suara TTS** yang akan digunakan. | Tidak | `Leda`, `Puck`, `Charon` |
| **`--api_key_file`** | `-k` | Jalur ke file yang berisi daftar **API Key Google AI**, dipisahkan baris baru. | Tidak | `api-keys.txt` |
| **`--ffmpeg_path`** | `-f` | Jalur manual ke **`ffmpeg.exe`**. Berguna jika tidak ada di PATH sistem. | Tidak | `C:\ffmpeg\bin\ffmpeg.exe` |
| **`--max_chars`** | | Batas **karakter maksimum per *chunk*** untuk diolah dalam satu permintaan API. | Tidak | `4800` (default) |
| **`--temperature`** | `-t` | Mengontrol **kreativitas/variasi suara** (semakin tinggi semakin bervariasi). | Tidak | `0.0` - `1.0` (default: `0.7`) |
| **`--max_retries`** | `-r` | Jumlah **upaya maksimum per *chunk*** sebelum mencoba API Key berikutnya atau gagal. | Tidak | `5` (default) |
| **`--base_delay`** | `-d` | **Jeda dasar (detik)** untuk mekanisme *retry* saat terjadi error sementara. | Tidak | `5` (default) |
| **`--no-delete`** | | **Mencegah penghapusan file *chunk*** audio sementara (`*_01.wav`, `*_02.wav`, dst.) setelah digabungkan. | Tidak | - |

## Kompilasi Executable

ikuti intruksi ini untuk mengkompilasinya menjadi executable:

- install uv `powershell -c "irm https://astral.sh/uv/install.ps1 | more"`
- jalankan uv: `uv sync`
- jalankan program: `uv run build/build_binary.py`

*Executable* yang dihasilkan akan berada di direktori `dist/`.

-----

## ⬇️ Unduh Executable

[Mediafire](https://www.mediafire.com/file/qv6hk5dw3neinj8/gtts-cli.zip/file)
