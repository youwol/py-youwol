FROM python:3.11-slim


RUN useradd --uid 10000 yw_app

RUN apt-get update \
    && apt-get install -y \
         ca-certificates \
         gcc \
         g++ \
         libffi-dev \
         brotli \
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY /requirements-docker.txt /
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir --upgrade -r "/requirements-docker.txt"

EXPOSE 8080
WORKDIR /opt/app

COPY /images/backends/entry_point.sh /
COPY /src/youwol/utils /opt/app/youwol/utils
COPY /src/youwol/backends /opt/app/youwol/backends/

USER 10000
ENV YOUWOL_SOURCES_PATH=/opt/app
ENTRYPOINT ["sh", "/entry_point.sh"]
