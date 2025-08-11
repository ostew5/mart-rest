FROM python:3.10-slim

WORKDIR /app

COPY phi3-backend.py .

RUN pip install torch==2.3.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install transformers

CMD ["python", "phi3-backend.py"]