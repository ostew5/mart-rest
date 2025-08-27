Assignment 1 - REST API Project - Response to Criteria
================================================

Overview
------------------------------------------------

- **Name:** Oliver Stewart
- **Student number:** n11588608
- **Application name:** Mart - RAG & LLM Powered Cover Letter Generator
- **Two line description:** A RAG & LLM powered REST API that automates the process of scraping a job description, matching the job description to relevant sections of an applicant's resume and generating a complete, formatted and rendered pdf cover letter for the applicant.


Core criteria
------------------------------------------------

### Containerise the app

- **ECR Repository name:**
- **Video timestamp:**
- **Relevant files:**
    - 

### Deploy the container

- **EC2 instance ID:** i-02f0ab8046a2cf8c5 (ec2-SouthEast2-n11588608-Mart)
- **Video timestamp:**

### User login

- **One line description:** Hard-coded uuid/passkey list. Using JWTs for sessions.
- **Video timestamp:**
- **Relevant files:**
    - `/app/pyapp/routers/user.py`

### REST API

- **One line description:** REST API with endpoints (as nouns) and HTTP methods (GET, POST, PUT), and appropriate status codes
- **Video timestamp:**
- **Relevant files:**
    - `/app/pyapp/app.py`
    - `/app/pyapp/routers/generate_cover_letter.py`
    - `/app/pyapp/routers/index_resume.py`

### Data types

#### First kind

- **One line description:** FAISS files
- **Type:** `.pkl`, Structured
- **Rationale:** Whole FAISS index must be loaded for fast FAISS similarity search, removes the need of a database.
- **Video timestamp:**
- **Relevant files:**
    - `/app/pyapp/routers/generate_cover_letter.py`
    - `/app/pyapp/routers/index_resume.py`

#### Second kind

- **One line description:** BIN files
- **Type:** `.bin`, Structured
- **Rationale:** Used in conjunction with FAISS index to store the raw text the FAISS index points to.
- **Video timestamp:**
- **Relevant files:**
  - `/app/pyapp/routers/generate_cover_letter.py`
  - `/app/pyapp/routers/index_resume.py`

#### Third kind

- **One line description:** PDF Cover Letter
- **Type:** `.pdf`, Unstructured
- **Rationale:** Store rendered pdf for user retrieval once cover letter generation job has completed.
- **Video timestamp:**
- **Relevant files:**
  - `/app/pyapp/routers/generate_cover_letter.py`
  - `/app/pyapp/routers/index_resume.py`

### CPU intensive task

 **One line description:** Uses Docker Model Runner with `hf.co/nomic-ai/nomic-embed-text-v1.5-GGUF:Q4_K_M` to get text embeddings for an applicant's resume and the job description. These text embeddings are used to get the "top-k" sections of the resume that relate to the job description fueling the Retrieval-Augmented Generation (RAG) step of generating a cover letter.
- **Video timestamp:** 
- **Relevant files:**
    - `/app/pyapp/routers/generate_cover_letter.py`
    - `/app/pyapp/routers/index_resume.py`

### CPU load testing

 **One line description:**
- **Video timestamp:** 
- **Relevant files:**
    - 

Additional criteria
------------------------------------------------

### Extensive REST API features

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### External API(s)

- **One line description:** Cover Letter Generation
- **Video timestamp:**
- **Relevant files:**
    - 

### Additional types of data

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### Custom processing

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### Infrastructure as code

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 

### Upon request

- **One line description:** Not attempted
- **Video timestamp:**
- **Relevant files:**
    - 