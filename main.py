import argparse
import re
import sys
import time
import logging
import os
import glob

# Konfigurasi Logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S' 
)

# --- Konfigurasi Global dan API Key Management ---
API_KEYS_LIST = []
current_api_key_index = 0

def get_base_path():
    """Get the path where the executable or script is running from."""
    if getattr(sys, 'frozen', False):
        # The script is running in a frozen executable (e.g., PyInstaller)
        # sys.executable is the path to the executable itself
        base_path = os.path.dirname(sys.executable)
    else:
        # The script is running in a normal Python environment
        # __file__ is the path to the script file
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return base_path

# FUNGSI DIPERBARUI: Menerima filepath sebagai argumen
def load_api_keys(filepath: str):
    """Memuat daftar API Key dari file teks."""
    global API_KEYS_LIST
    try:
        with open(filepath, 'r') as f:
            keys = [line.strip() for line in f if line.strip()]
            if not keys:
                raise ValueError(f"File '{filepath}' kosong atau tidak berisi key.")
            API_KEYS_LIST = keys
            logger.info(f"Ditemukan {len(API_KEYS_LIST)} API Key dari {filepath}.")
    except FileNotFoundError:
        raise FileNotFoundError(f"File API Key tidak ditemukan di: {filepath}. Buat file dan isi key di dalamnya.")

def get_current_api_key():
    """Mengembalikan API Key yang saat ini digunakan."""
    if not API_KEYS_LIST:
        return None
    index = current_api_key_index % len(API_KEYS_LIST)
    return API_KEYS_LIST[index]

def rotate_api_key():
    """Memutar indeks ke API Key berikutnya."""
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(API_KEYS_LIST)
    logger.warning(f"API Key diputar. Index berikutnya: {current_api_key_index}")

# --- Fungsi Utility WAV dan SSML Converter ---
def save_audio_to_wav(filename: str, pcm_data: bytes, chunk_index: int):
    import wave
    """Menulis data PCM audio biner ke file WAV dengan indeks chunk."""
    final_filename = f"{os.path.splitext(filename)[0]}_{chunk_index:02d}.wav"
    try:
        with wave.open(final_filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)
        logger.info(f"✅ File audio berhasil disimpan ke: {final_filename}")
    except Exception as e:
        logger.error(f"❌ Error saat menyimpan file WAV: {e}")

def convert_custom_prompt_to_tts_format(custom_prompt: str) -> str:
    """Mengubah format kustom [INSTRUKSI_SUARA]/[JEDA] ke format Gemini TTS/SSML."""
    
    prompt = re.sub(r'\[JEDA: (\d+\.\d+) detik\]', lambda m: f'<break time="{int(float(m.group(1)) * 1000)}ms"/>', custom_prompt)
    prompt = prompt.replace("START_SCRIPT", "").replace("---", "").replace("[TEKS_SCRIPT]", "")
    prompt = re.sub(r'\[INSTRUKSI_SUARA:\s*(.*?)\]', r'Say with a \1 voice:', prompt)
    prompt = "\n".join([line.strip() for line in prompt.splitlines() if line.strip()])
    
    return prompt.strip()

# --- Fungsi Pembagi Teks (Tidak Berubah) ---
def split_text_into_chunks_by_chars(full_text: str, max_chars_per_chunk: int) -> list[str]:
    # ... (Logika pembagian chunk tetap sama) ...
    clean_text = ' '.join(full_text.split())
    chunks = []
    current_start = 0
    total_length = len(clean_text)

    while current_start < total_length:
        remaining_length = total_length - current_start
        if remaining_length <= max_chars_per_chunk:
            chunks.append(clean_text[current_start:])
            break
            
        max_end = current_start + max_chars_per_chunk
        split_point = -1
        search_area_start = max_end - 200
        if search_area_start < current_start:
             search_area_start = current_start

        match = re.search(r'([.?!]|\<\/break\/\>)\s', clean_text[search_area_start:max_end], re.DOTALL | re.IGNORECASE)
        
        if match:
            relative_index = match.end()
            split_point = search_area_start + relative_index
        
        if split_point == -1 or split_point <= current_start:
            split_point = max_end
            
        chunk = clean_text[current_start:split_point].strip()
        chunks.append(chunk)
        current_start = split_point
        
    logger.info(f"Teks dibagi menjadi {len(chunks)} chunk (Max {max_chars_per_chunk} karakter/chunk) untuk menghemat RPD.")
    return chunks

# --- Fungsi Utama dengan Rotasi Key (Tidak Berubah) ---
def make_tts_request_with_retry(
    prompt: str, 
    voice: str, 
    base_filename: str, 
    chunk_index: int, 
    max_retries: int, 
    base_delay: int, 
    temperature: float = 0.7
):
    
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
        
    """Melakukan permintaan TTS dengan retry dan rotasi API key."""
    
    max_key_attempts = len(API_KEYS_LIST)
    
    for attempt in range(max_key_attempts):
        api_key = get_current_api_key()
        
        try:
            logger.info(f'Mencoba request dengan Key index: {current_api_key_index} (Percobaan {attempt + 1}/{max_key_attempts})')
            
            client = genai.Client(api_key=api_key)
            
            config = types.GenerateContentConfig(
                temperature=temperature,    
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=prompt,
                config=config
            )

            data = response.candidates[0].content.parts[0].inline_data.data
            save_audio_to_wav(base_filename, data, chunk_index)
            return  

        except APIError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                logger.warning(f"⚠️ Kuota RPD Key index {current_api_key_index} habis.")
                rotate_api_key()
            else:
                delay = base_delay * (2 ** attempt)  
                logger.warning(f"⚠️ Error sementara ({e}). Mencoba lagi dalam {delay:.1f} detik.")
                time.sleep(delay)
                
    logger.error(f"❌ Gagal total memproses chunk {chunk_index} setelah semua upaya dan rotasi key.")
    raise Exception(f"Chunk {chunk_index} gagal total diproses.")

def generate_audio_for_chunks(
    full_prompt: str, 
    voice: str, 
    base_filename: str, 
    max_chars_per_chunk: int,
    max_retries: int, 
    base_delay: int, 
    temperature: float = 0.7
):
    """Memecah teks dan menghasilkan audio untuk setiap chunk."""
    
    clean_prompt = convert_custom_prompt_to_tts_format(full_prompt)
    text_chunks = split_text_into_chunks_by_chars(clean_prompt, max_chars_per_chunk)
    total_chunks = len(text_chunks)
    
    for i, chunk in enumerate(text_chunks):
        logger.info(f"\n--- Memproses Chunk {i + 1} dari {total_chunks} ---")
        
        make_tts_request_with_retry(
            prompt=chunk, 
            voice=voice, 
            base_filename=base_filename,
            chunk_index=i + 1,
            max_retries=max_retries, 
            base_delay=base_delay, 
            temperature=temperature
        ) 
        time.sleep(0.5)

# --- Fungsi Penggabungan Audio (Tidak Berubah) ---
def combine_audio_chunks(base_filename: str, output_filename: str = 'final_narasi.wav', delete_chunks: bool = True):
    # import pydub after ffmpeg path initial
    from pydub import AudioSegment # Import pydub di awal
    
    """Menggabungkan semua file chunk audio (*_01.wav, *_02.wav, dst.) menjadi satu file."""
    search_pattern = f"{base_filename}_*.wav"
    file_list = sorted(glob.glob(search_pattern))
    
    if not file_list:
        logger.error(f"❌ Tidak ditemukan file WAV yang cocok dengan pola '{search_pattern}'.")
        return

    logger.info(f"Ditemukan {len(file_list)} file untuk digabungkan.")
    combined_audio = AudioSegment.empty()
    
    try:
        for file_path in file_list:
            logger.info(f"⏳ Menggabungkan: {file_path}")
            chunk_audio = AudioSegment.from_wav(file_path)
            combined_audio += chunk_audio
                
        combined_audio.export(output_filename, format="wav")

        if delete_chunks:
            for file_path in file_list:
                os.remove(file_path)
                logger.debug(f"🗑️ File chunk sementara dihapus: {file_path}")
        
        logger.info(f"✅ Penggabungan Selesai! File disimpan sebagai: {output_filename}")
        
    except FileNotFoundError:
        logger.error("❌ Error: FFmpeg tidak ditemukan!")
        logger.error("Pastikan FFmpeg terinstal dan PATH sistem telah dikonfigurasi dengan benar, atau gunakan argumen --ffmpeg_path.")
    except Exception as e:
        logger.error(f"❌ Terjadi error saat memproses audio: {e}")

# ----------------------------------------------------
# --- EKSEKUSI UTAMA CLI ---
# ----------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Gemini Text-to-Speech Generator (Preview TTS) dengan Rotasi API Key.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Argumen Wajib
    parser.add_argument(
        '-p', '--prompt', 
        type=str, 
        required=True, 
        help="Teks narasi (Say [gaya]: [teks] dan <break time='Nms'/>)."
    )
    
    # Argumen File/Path
    parser.add_argument(
        '-v', '--voice', 
        type=str, 
        default='Zubenelgenubi', 
        help="Nama suara TTS (Default: Zubenelgenubi)."
    )
    parser.add_argument(
        '-o', '--output_name', 
        type=str, 
        default='narasi_output', 
        help="Nama dasar file output (Default: narasi_output)."
    )
    parser.add_argument(
        '-k', '--api_key_file', 
        type=str, 
        default='api-keys.txt', 
        help="Path ke file yang berisi daftar API Key (Default: api-keys.txt)."
    )
    parser.add_argument(
        '-f', '--ffmpeg_path', 
        type=str, 
        default=os.environ.get("FFMPEG_PATH", "ffmpeg.exe"),
        help="Path manual ke executable FFmpeg (Default: mencari di PATH atau ffmpeg.exe)."
    )
    
    # Argumen Kontrol Kualitas/Rate Limit
    parser.add_argument(
        '--max_chars', 
        type=int, 
        default=4800, 
        help="Batas karakter per chunk untuk menghemat RPD (Default: 4800)."
    )
    parser.add_argument(
        '-t', '--temperature', 
        type=float, 
        default=0.7, 
        help="Kontrol kreativitas dan variasi suara (0.0 hingga 1.0). Default: 0.7."
    )
    parser.add_argument(
        '-r', '--max_retries', 
        type=int, 
        default=5, 
        help="Jumlah upaya maksimum sebelum key dirotasi atau gagal total (Default: 5)."
    )
    parser.add_argument(
        '-d', '--base_delay', 
        type=int, 
        default=5, 
        help="Detik dasar untuk jeda eksponensial saat error sementara (Default: 5 detik)."
    )
    
    # Argumen Flag
    parser.add_argument(
        '--no-delete', 
        action='store_true', 
        help="Jangan hapus file chunk sementara setelah penggabungan."
    )

    args = parser.parse_args()
    
    # --- PENANGANAN INPUT PROMPT ---
    final_prompt = args.prompt
    
    # Cek apakah input adalah path file (.txt)
    if final_prompt.lower().endswith('.txt') and os.path.exists(final_prompt):
        try:
            with open(final_prompt, 'r', encoding='utf-8') as f:
                raw_prompt_content = f.read()
            
            # Hapus baris kosong atau whitespace yang berlebihan
            final_prompt = '\n'.join([line.strip() for line in raw_prompt_content.splitlines() if line.strip()])
            
            logger.info(f"📚 Prompt berhasil dimuat dari file: {args.prompt} ({len(final_prompt)} karakter)")
        except Exception as e:
            logger.critical(f"❌ Gagal membaca file prompt '{args.prompt}': {e}")
            return # Keluar dari program jika gagal membaca file
    else:
        # Jika bukan file atau file tidak ada, perlakukan sebagai string prompt
        logger.info("📝 Prompt diterima sebagai string langsung dari CLI.")

    # --- KONFIGURASI FFMPEG DARI ARGUMEN CLI ---
    # ... (Logika konfigurasi FFmpeg dan Eksekusi Utama tetap sama) ...
    try:
        args.ffmpeg_path = os.path.abspath(args.ffmpeg_path)
        if os.path.exists(args.ffmpeg_path):
            os.environ["FFMPEG_PATH"] = args.ffmpeg_path
            os.environ["PATH"] += os.pathsep + os.path.dirname(args.ffmpeg_path)
            logging.info(f"✅ Path FFmpeg diatur dari CLI: {args.ffmpeg_path}")
        else:
            logging.warning(f"⚠️ FFmpeg tidak ditemukan di path CLI: {args.ffmpeg_path}. Mengandalkan PATH sistem.")
            # when not custom ffmpeg path, use default
            base_dir = get_base_path()
            ffmpeg_bin_dir = os.path.join(base_dir, 'ffmpeg/')
            os.environ["PATH"] = ffmpeg_bin_dir
    except Exception as e:
        logging.error(f"❌ Gagal mengatur variabel lingkungan FFmpeg: {e}")    
        # when not custom ffmpeg path, use default
        base_dir = get_base_path()
        ffmpeg_bin_dir = os.path.join(base_dir, 'ffmpeg/')
        os.environ["PATH"] = ffmpeg_bin_dir
        
    try:

        load_api_keys(args.api_key_file)

        generate_audio_for_chunks(
            full_prompt=final_prompt, 
            voice=args.voice, 
            base_filename=args.output_name,
            max_chars_per_chunk=args.max_chars,
            max_retries=args.max_retries, 
            base_delay=args.base_delay, 
            temperature=args.temperature
        )

        combine_audio_chunks(
            base_filename=args.output_name,
            output_filename=f"final_{args.output_name}.wav",
            delete_chunks=not args.no_delete
        )

    except (FileNotFoundError, ValueError) as e:
        logger.critical(f"❌ Error Konfigurasi: {e}")
    except Exception as e:
        logger.critical(f"Gagal menjalankan proses utama: {e}")

if __name__ == "__main__":
    main()
#