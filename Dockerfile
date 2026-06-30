# 1. Gunakan dasar Linux yang sudah ada Python versi stabil
FROM python:3.10-slim

# 2. Instal ffmpeg (Alat wajib untuk memotong & membaca file audio)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /lib/apt/lists/*

# 3. Buat folder kerja di dalam server
WORKDIR /app

# 4. Salin daftar requirements dan instal semua alat bantu AI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Salin seluruh kode main.py kita ke dalam server
COPY main.py .

# 6. Jalankan server FastAPI pada port 7860 (Port standar Hugging Face)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
