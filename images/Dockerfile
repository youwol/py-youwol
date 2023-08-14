FROM python:3.9-slim


RUN apt-get update \
    && apt-get install -y \
        ca-certificates brotli\
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /root

COPY /requirements-docker.txt /root/
RUN pip3 install --no-cache-dir --upgrade -r "requirements-docker.txt"

COPY /src/youwol/utils /root/youwol/utils
COPY /src/youwol/backends/common /root/youwol/backends/common

ARG backend
COPY /src/youwol/backends/$backend /root/youwol/backends/$backend

ENV backend=$backend
ENTRYPOINT uvicorn youwol.backends.$backend.deployment:app --host=0.0.0.0 --no-server-header --port=8080
