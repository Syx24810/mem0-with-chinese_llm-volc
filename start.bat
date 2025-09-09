@echo off
echo === Starting Memory Chat Assistant ===
echo (Supports model selection and memory-mode toggle)

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker not found. Please install Docker Desktop first.
    pause
    exit /b
)

echo 1. Building and starting services...
docker-compose up -d --build

echo 2. Waiting for services to start...
timeout /t 15 /nobreak

echo 3. Checking service health...
echo   - Qdrant status
curl -s http://localhost:6333 || echo   Connection failed: please wait for Qdrant to start

echo   - Ollama status
curl -s http://localhost:11434/api/tags || echo   Connection failed: please wait for Ollama to start

echo 4. Initializing services...
timeout /t 5 /nobreak

echo === Services are running ===
echo Web UI: http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.
echo Features:
echo - Model selection: choose different models in the web UI
echo - Memory mode: toggle memory on/off for comparison
echo.
echo Press Ctrl+C to stop viewing logs
echo.

REM Show logs
docker-compose logs -f