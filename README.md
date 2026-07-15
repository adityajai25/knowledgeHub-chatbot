# KnowledgeHub AI

KnowledgeHub AI is a two-part application:

- A FastAPI backend for authentication, document upload, semantic search, and chat.
- A Vite + React frontend for the user interface.

The frontend talks to the backend at `http://localhost:8000`, so the backend must be running on that port for the app to work.

## Requirements

Install these before setting up the project on another machine:

- Python 3.9 or newer
- Node.js 18 or newer
- npm
- PostgreSQL
- `tesseract` and `poppler` for PDF OCR support

### macOS

```bash
brew install python node postgresql tesseract poppler
```

### Ubuntu or Debian

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip nodejs npm postgresql tesseract-ocr poppler-utils
```

### Windows

Install Python, Node.js, and PostgreSQL from their official installers. For OCR support, install Tesseract and Poppler separately and make sure both are available on your `PATH`.

## Project Setup

Clone the repository, then set up the backend and frontend separately.

### 1. Configure the backend

Create a virtual environment and install Python dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory:

```bash
cp .env.example .env
```

Update `DATABASE_URL` in `backend/.env` so it points to your PostgreSQL instance. The default application settings expect a Postgres database that the backend can reach locally or on your network.

Example:

```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/knowledgehub"
```

If you want Hugging Face hosted inference, also set:

```env
HF_API_KEY="your_huggingface_key"
```

Other Hugging Face settings can be left at their defaults unless you want to change them.

### 2. Configure the frontend

Install frontend dependencies:

```bash
cd ../frontend
npm install
```

## Running the Application

### Option 1: Use the launcher script

From the repository root:

```bash
./start-app.sh
```

This script:

- Starts the backend with Uvicorn on `http://127.0.0.1:8000`
- Starts the frontend dev server on `http://127.0.0.1:5173`
- Writes logs to `.backend.log` and `.frontend.log`

If the script is not executable, run:

```bash
chmod +x start-app.sh
```

### Option 2: Start each service manually

#### Backend

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH="$PWD"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## Usage

Open the frontend at `http://127.0.0.1:5173`.

The main flows are:

- Register or log in from the authentication page
- Upload PDF or TXT documents from the dashboard
- Search uploaded content semantically
- Ask questions about the uploaded documents

## Backend Notes

- The backend initializes its database tables on startup.
- Uploaded files are stored in `backend/uploads`.
- Document text extraction supports plain text and PDF files.
- For scanned PDFs, OCR falls back to `pdf2image` plus `pytesseract`, which is why `poppler` and `tesseract` are required.

## Troubleshooting

- If login or upload requests fail, confirm that the backend is running on port `8000`.
- If uploads fail for scanned PDFs, check that `tesseract` and `poppler` are installed and available on the machine.
- If the backend cannot connect to the database, verify the `DATABASE_URL` value in `backend/.env` and that PostgreSQL is running.
- If the frontend cannot reach the backend from another host, update the hardcoded API URL in `frontend/src/App.jsx` from `http://localhost:8000` to the correct backend address.

## Folder Overview

- `backend/` - FastAPI app, database code, embeddings, and upload handling
- `frontend/` - React app built with Vite
- `start-app.sh` - Convenience script to launch both services locally
