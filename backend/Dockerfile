FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libglib2.0-0 libharfbuzz0b libfribidi0 \
    libffi8 libxml2 libxslt1.1 libjpeg62-turbo zlib1g \
    fontconfig fonts-dejavu-core pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app_v1
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY app_v1/ app_v1/

COPY fonts/*.ttf /usr/local/share/fonts/
RUN fc-cache -f -v

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app_v1.app:app", "--host", "0.0.0.0", "--port", "8080"]