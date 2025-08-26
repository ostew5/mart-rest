# Mart - AI-Powered Cover Letter Generator

> **README.md** generated with **NotebookLM** + **ChatGPT 5**

An AI-driven **cover letter generator** built with **FastAPI**, designed to help users create tailored cover letters by indexing their resumes and applying to job listings.  

The system integrates **RAG and LLM-based cover letter generation, PDF rendering, authentication, and rate limiting**—all packaged in a scalable Dockerized application.

---

## 🚀 Features

### 🔑 Core Functionality
- **Resume Indexing** (`/index_resume`)  
  Upload a PDF resume → extract text → chunk + embed → store in **FAISS index** → persist to **AWS S3** (`resume-storage-ostew5`) → runs as **background task**.
  
- **Cover Letter Generation** (`/generate_cover_letter`)  
  Input job listing URL + resume UUID → fetch & parse listing via **BeautifulSoup** + `job-listing-selectors.json` → retrieve relevant resume chunks from FAISS → construct prompt → generate letter via **Gemini API (gemini-2.5-pro)** → render to PDF with **Jinja2 + Weasyprint** → upload to **S3** → runs as **background task**.
  
- **Job Management**  
  - Status: `/index_resume/status/{job_id}`, `/generate_cover_letter/status/{job_id}`  
  - Result: `/generate_cover_letter/result/{job_id}` (PDF download)

---

## 🛠️ Technical Stack

- **Framework**: FastAPI  
- **Server**: Uvicorn  
- **Language**: Python 3.11-slim  
- **Dependencies**: `requests`, `openai`, `pypdf`, `bs4`, `faiss-cpu`, `weasyprint`, `jinja2`, `boto3`, `pyjwt`  
- **Embedding Model**: nomic-embed-text-v1.5 - GGUF **ran with Docker Model Runner** (`hf.co/nomic-ai/nomic-embed-text-v1.5-GGUF:Q4_K_M`)
- **LLM**: Gemini API (`gemini-2.5-pro`)  
- **Vector DB**: FAISS  
- **Storage**: AWS S3 (`resume-storage-ostew5`)  
- **PDF Generation**: Jinja2 + Weasyprint  
- **Containerization**: Docker (`Dockerfile`)  
- **Orchestration**: Docker Compose (`docker-compose.yml`)  
- **Config Management**: Environment variables (`.env` excluded from VCS)

---

## 🔒 User Management & Security

- **Authentication**: `/user/login` with `uuid` + `passkey` → JWT token  
- **Protected Endpoints**: `/index_resume/upload`, `/generate_cover_letter/start` require JWT  
- **Subscriptions**: `basic` & `premium` tiers  
- **Rate Limiting**: Defined in `rate-limits.json` per tier + request type  
  - Example: `basic` → 1 resume + 1 cover letter / hour

---

## 📦 Deployment

1. Clone repo & set up `.env` with required secrets:  
   - `GEMINI_API_KEY`  
   - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`  
   - `JWT_SECRET`

2. Build & run with Docker Compose:
   ```bash
   docker compose up --build
   ```
