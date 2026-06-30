import os
import shutil
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import whisper
import google.genai as genai
import requests
from pydub import AudioSegment

app = FastAPI()

# Izinkan Web Vercel kamu nanti untuk mengakses Backend ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Nanti bisa diganti dengan URL Vercel-mu jika sudah jadi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# KONFIGURASI KUNCI (Gunakan kunci milikmu yang sudah teruji)
GEMINI_API_KEY = "AQ.Ab8RN6IwrIAcAyc5anEMlhcNkQWnB8ldRWtPjKXk8StbdRT6Fw"
GSCRIPT_URL = "https://script.google.com/macros/s/AKfycbzFmHspd31V3Kh1W3dO9x4ncQ81v-2y_04UdUpnKqttF3xLE6tBpfVx1wTI2eO5-12y/exec"

# Load model Whisper sekali saja saat server menyala agar hemat waktu
print("Sedang memuat model Whisper...")
model_whisper = whisper.load_model("small")
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# FUNGSI LATAR BELAKANG (Ini yang bekerja saat kamu ditinggal ngopi)
def proses_koreksi_murojaah(file_path: str):
    try:
        print(f"Memulai pemrosesan latar belakang untuk: {file_path}")
        
        # 1. Potong otomatis per 10 menit jika audio panjang
        audio = AudioSegment.from_file(file_path)
        sepuluh_menit = 10 * 60 * 1000
        potongan_audio = [audio[i:i+sepuluh_menit] for i in range(0, len(audio), sepuluh_menit)]
        
        teks_kasar_total = ""
        laporan_koreksi_total = ""
        
        for index, potong in enumerate(potongan_audio):
            nama_sementara = f"temp_{index}.mp3"
            potong.export(nama_sementara, format="mp3")
            
            # Whisper mendengarkan
            result = model_whisper.transcribe(nama_sementara, language="ar")
            teks_kasar = result["text"]
            teks_kasar_total += teks_kasar + " "
            
            # Gemini mengoreksi (Format Poin-Poin Ringkas pesananmu)
            perintah_koreksi = f"""
            Kamu adalah AI Koreksi Hafalan Al-Qur'an. Bandingkan teks hasil rekaman ini dengan mushaf asli:
            "{teks_kasar}"
            Berikan hasil koreksi HANYA dalam bentuk poin-poin singkat dengan format persis seperti ini, tanpa salam, tanpa mukadimah, dan tanpa penutup:
            - Kata Salah -> Koreksi yang Benar (Catatan singkat)
            Jika bagian ini tidak ada kesalahan, cukup tulis: "Bagian ini aman/lancar".
            """
            response = client_gemini.models.generate_content(model='gemini-2.5-flash', contents=perintah_koreksi)
            laporan_koreksi_total += f"\n[Sesi Menit ke-{index*10}]\n" + response.text + "\n"
            
            # Hapus potongan sementara
            if os.path.exists(nama_sementara):
                os.remove(nama_sementara)
        
        # 2. Kirim laporan ke Google Sheets
        payload = {
            "menit": "Sesi Web Otomatis",
            "bacaan_saya": teks_kasar_total[:4000],
            "semestinya": laporan_koreksi_total
        }
        requests.post(GSCRIPT_URL, json=payload)
        print("Analisis sukses dan data terkirim ke Google Sheets!")

    except Exception as e:
        print(f"Terjadi kesalahan di background: {str(e)}")
    
    finally:
        # 3. PENGHAPUSAN OTOMATIS: File rekaman utama langsung dihapus dari server setelah selesai biar bersih
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File master {file_path} telah dihapus otomatis.")

# JALUR UTAMA (ENDPOINT) UNTUK MENERIMA UPLOAD DARI WEB VERCEL
@app.post("/upload")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Simpan file yang masuk untuk sementara
    file_location = f"master_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # PERINTAH KUNCI: Lempar proses ke latar belakang, lalu langsung bebaskan HP pengguna!
    background_tasks.add_task(proses_koreksi_murojaah, file_location)
    
    # Respons instan ke Web Vercel agar HP kamu tahu upload sudah sukses dan layar bisa dimatikan
    return {"status": "success", "message": "File berhasil diterima! AI sedang memproses di latar belakang, silakan tutup halaman ini dan silakan minum kopi."}
