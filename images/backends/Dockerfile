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



COPY /src/youwol/backends /opt/app/youwol/backends
COPY /images/backends/entry_point.sh /opt/app

USER 10000
EXPOSE 8080
ENV YOUWOL_SOURCES_PATH=/opt/app
ENTRYPOINT ["sh", "/opt/app/entry_point.sh"]
