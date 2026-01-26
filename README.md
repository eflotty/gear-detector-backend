# Gear Detector Backend API

FastAPI backend for Gear Detector iOS app - identifies guitar gear used by artists in specific songs.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Create database:
```bash
createdb geardetector
```

4. Run the server:
```bash
python -m src.main
```

Server will be available at http://localhost:8000

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

See `.env.example` for all required configuration.
