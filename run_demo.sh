#!/bin/bash
# Script khởi chạy nhanh DION Healthcare AI Demo Workspace
cd "$(dirname "$0")"
source venv/bin/activate
echo "🚀 Đang khởi động DION Healthcare AI Demo Workspace..."
streamlit run app.py
