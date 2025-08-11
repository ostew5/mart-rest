FROM python:3.10-slim

# Stable Layers

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application Code

WORKDIR /app
COPY phi3-backend.py .
CMD ["python", "phi3-backend.py"]