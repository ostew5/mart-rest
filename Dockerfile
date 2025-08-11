FROM python:3.10-slim

WORKDIR /app

COPY phi3-backend.py .

RUN pip install torch transformers

CMD ["python", "phi3-backend.py"]