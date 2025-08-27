# Mart - Cover Letter Generator

A RAG and LLM powered REST API that automates the process of **indexing resumes** and **generating tailored cover letters** based on job listings.  
Built with **FastAPI**, **FAISS**, **S3 storage**, **Docker Model Runner**, and the **Gemini API**, it provides an end-to-end pipeline with authentication, subscription-based rate limiting, and PDF generation.

---

## 🚀 Features

### Resume Indexing (`/index_resume`)
- Upload PDF resumes.
- Extract and clean text (normalize bullets, spaces, newlines).
- Chunk text with overlaps for better context.
- Generate embeddings with a configurable model.
- Store embeddings in a **FAISS index** and persist to **S3**.
- Track job status and enforce **subscription-based file size/limits**.

### Cover Letter Generation (`/generate_cover_letter`)
- Provide a **LinkedIn job listing URL** + resume ID.
- Scrape job details (title, company, location, description).
- Retrieve relevant resume info via FAISS similarity search.
- Build a structured prompt for the **Gemini API**.
- Generate JSON-based cover letter content.
- Render PDF using **Jinja2** + **WeasyPrint** template.
- Upload PDF to **S3** and allow retrieval.
- Enforce **rate limits** per subscription level.

### User Management (`/user`)
- `/login` with UUID + passkey → returns JWT.
- Subscription levels:
  - **Basic**: stricter limits.
  - **Premium**: higher request/file size limits.

---

## 🛠️ Tech Stack

- **FastAPI** – API framework  
- **FAISS** – vector similarity search  
- **S3 (boto3)** – resume & letter storage
- **Docker Model Runner** – Embedding model for RAG
- **Gemini API** – LLM cover letter generation  
- **WeasyPrint + Jinja2** – PDF rendering  
- **JWT** – authentication  
- **Docker & Docker Compose** – containerization  

---

## 📦 Requirements

- **Docker & Docker Compose**
- **Python 3.11 (slim base image)** with system dependencies:
  - `libcairo2`, `libpango-1.0-0`, `libgdk-pixbuf-2.0-0`, `libglib2.0-0`,  
    `libharfbuzz0b`, `libfribidi0`, `libffi8`, `libxml2`, `libxslt1.1`,  
    `libjpeg62-turbo`, `zlib1g`, `fontconfig`, `fonts-dejavu-core`
- **Python packages** (see `requirements.txt`):
  - `fastapi`, `uvicorn`, `requests`, `openai`, `pypdf`, `python-multipart`,  
    `beautifulsoup4`, `faiss-cpu`, `weasyprint`, `jinja2`, `boto3`, `pyjwt`

---

## ⚙️ Configuration

### Environment Variables (`.env`)
| Variable | Description |
|----------|-------------|
| `GEMINI_API_URL` | Gemini API endpoint |
| `GEMINI_API_KEY` | Gemini API key |
| `S3_BUCKET_NAME` | AWS S3 bucket |
| `S3_REGION` | AWS region |
| `AWS_ACCESS_KEY_ID` | AWS key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret |
| `JWT_SECRET` | Secret for signing JWTs |

---

## 📂 Project Structure

pyapp/
├── main.py                  # FastAPI entrypoint
├── templates/letter.html    # Cover letter template
├── job-listing-selectors.json
├── helpers/subscription-limits.json
└── ... (resume + letter logic)
fonts/
└── \*.ttf
requirements.txt
docker-compose.yml

---

## ▶️ Running Locally

```bash
# Build and start
docker-compose up --build
````

You may need to install a version of Docker with Docker Model Runner:

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install ca-certificates curl gnupg lsb-release -y
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo usermod -aG docker $USER
```

App runs at: [http://localhost:8080](http://localhost:8080)

---

## 🔑 Authentication

* **Login:**
  `POST /user/login` with `{ "uuid": "...", "passkey": "..." }`
  → returns a JWT for authenticated requests.

* Pre-configured users exist for testing (`basic`, `premium`).

---

## 📖 API Overview

* **POST /index\_resume** → upload and index a resume PDF
* **GET /index\_resume/{id}/status** → check indexing status
* **POST /generate\_cover\_letter** → generate cover letter from job URL + resume ID
* **GET /generate\_cover\_letter/{id}/status** → check generation status
* **GET /generate\_cover\_letter/{id}/pdf** → retrieve generated cover letter PDF
* **POST /user/login** → user login (JWT)

---

## 📜 License

MIT License – feel free to use, modify, and distribute.

---
