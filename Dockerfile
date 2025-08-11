FROM python:3.11-slim

# Smaller, faster Python
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Runtime libs for OpenBLAS wheel (no toolchain needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Pull prebuilt wheel from extra index
RUN pip install --upgrade pip && pip install -r requirements.txt

# Download GGUF at build time (optional—can mount instead)
RUN mkdir -p /models && python - <<'PY'
from huggingface_hub import hf_hub_download
import shutil, os
repo = "ggml-org/SmolLM3-3B-GGUF"
fname = "SmolLM3-Q4_K_M.gguf"
src = hf_hub_download(repo_id=repo, filename=fname)
shutil.copy(src, os.path.join("/models", fname))
print("Model copied to /models/" + fname)
PY

# Your app
COPY app.py .

# Defaults (override at runtime if needed)
ENV MODEL_PATH=/models/SmolLM3-3B-Q4_K_M.gguf \
    N_THREADS=8 \
    N_CTX=4096

CMD ["python", "app.py"]
