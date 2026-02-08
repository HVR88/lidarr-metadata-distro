FROM python:3.9-alpine

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache build-base git curl

RUN pip install --no-cache-dir poetry

WORKDIR /metadata

# Build context is the TOP of lidarr-metadata-distro, so this path exists.
COPY upstream/lidarr-metadata /metadata

RUN poetry install --no-interaction --no-ansi

EXPOSE 5001
ENTRYPOINT ["lidarr-metadata-server"]
