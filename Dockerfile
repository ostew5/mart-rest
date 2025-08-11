FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Setup llama-cpp-python (credit to: 3x3cut0r/docker/llama-cpp-python/Dockerfile line 16 on GitHub)
RUN apk add --no-cache --virtual .build-deps build-base ccache cmake ninja-build && \
    apk add --no-cache curl git gfortran openblas-dev runit tzdata && \
    rm -rf /var/lib/apt/lists/* && \
    python -m venv /venv && \
    /venv/bin/pip install --upgrade pip \
        anyio \
        pytest \
        scikit-build \
        setuptools \
        fastapi \
        uvicorn \
        sse-starlette \
        pydantic-settings \
        starlette-context \
        huggingface-hub \
        huggingface_hub[cli] && \
    LLAMA_OPENBLAS=ON \
    CMAKE_ARGS=$CMAKE_ARGS \
    /venv/bin/pip install --no-cache-dir llama-cpp-python --verbose && \
    apk del --no-network .build-deps && \
    mkdir -p \
        /runit-services/llama-cpp-python \
        /runit-services/syslogd && \
    echo -e "#!/bin/sh\nbusybox syslogd -n -O /dev/stdout" > \
        /runit-services/syslogd/run && \
    echo -e "#!/bin/sh\n/venv/bin/python3 -B -m llama_cpp.server --model /model/model.gguf" > \
        /runit-services/llama-cpp-python/run && \
    chmod +x /runit-services/syslogd/run \
        /runit-services/llama-cpp-python/run

WORKDIR /models
RUN curl -L "https://huggingface.co/ggml-org/SmolLM3-3B-GGUF/resolve/main/SmolLM3-Q4_K_M.gguf" \
    -o SmolLM3-Q4_K_M.gguf

WORKDIR /app

COPY app.py .

CMD ["python", "app.py"]
