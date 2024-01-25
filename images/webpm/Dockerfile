FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 10000 webpm

RUN apt-get update \
    && apt-get install -y \
        ca-certificates brotli\
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

COPY requirements-docker.txt /app
RUN pip3 install --no-cache-dir --upgrade -r "requirements-docker.txt"

COPY /src/youwol/utils /app/youwol/utils
COPY /src/youwol/backends/common /app/youwol/backends/common
COPY /src/youwol/backends/webpm /app/youwol/backends/webpm
COPY /src/youwol/backends/webpm/default-logging.yaml /app/logging.yaml


USER 10000
ENTRYPOINT [ "uvicorn", "youwol.backends.webpm.main:app", "--host", "0.0.0.0", "--no-server-header", "--log-config", "/opt/app/logging.yaml" ]
