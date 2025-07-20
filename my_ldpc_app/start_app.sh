#!/bin/bash
echo "Starting LDPC Designer Application..."
echo

echo "[1/3] Starting Backend Server..."
cd backend
python3 main.py &
BACKEND_PID=$!

echo "[2/3] Waiting for backend to start..."
sleep 3

echo "[3/3] Starting Flutter Web Application..."
cd ..
flutter run -d chrome

echo
echo "Application should now be running!"
echo "Backend: http://127.0.0.1:5000"
echo "Frontend: http://localhost:port (check Flutter output)"
echo

# 清理后台进程
trap "kill $BACKEND_PID" EXIT
