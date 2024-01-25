FROM python:3.12-slim

WORKDIR /opt/app

RUN useradd --uid 10000 app

RUN apt-get update \
    && apt-get install -y \
         ca-certificates \
         brotli \
         gcc \
         g++ \
         libffi-dev \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY /requirements-docker.txt /opt/app
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir --upgrade -r "/opt/app/requirements-docker.txt"

COPY /src/youwol/utils /opt/app/youwol/utils



COPY /src/youwol/backends/common /opt/app/youwol/backends/common
COPY /src/youwol/backends/webpm /opt/app/youwol/backends/webpm
COPY /images/webpm/default-logging.yaml /opt/app/logging.yaml


USER 10000
EXPOSE 8000
ENTRYPOINT [ "uvicorn", "youwol.backends.webpm.main:app", "--host", "0.0.0.0", "--no-server-header", "--log-config", "/opt/app/logging.yaml" ]
