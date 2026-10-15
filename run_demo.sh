#!/bin/bash
# Script khởi chạy DION Healthcare AI Platform (FastAPI + Tailwind CSS)
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Đang khởi động DION Healthcare AI (Giao diện Hiện đại Tailwind CSS)..."
echo "🌐 Truy cập tại: http://localhost:8000"
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
