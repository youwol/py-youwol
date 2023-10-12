FROM python:3.9-slim


RUN apt-get update \
    && apt-get install -y \
        ca-certificates brotli\
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /opt

COPY /requirements-docker.txt /opt/
RUN pip3 install --no-cache-dir --upgrade -r "requirements-docker.txt"

COPY /images/entry_point.sh /
COPY /src/youwol/utils /opt/youwol/utils
COPY /src/youwol/backends /opt/youwol/backends/

ENV YOUWOL_SOURCES_PATH=/opt
ENTRYPOINT ["sh", "/entry_point.sh"]
