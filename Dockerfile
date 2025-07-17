FROM debian:12-slim AS builder
RUN apt-get update && apt-get install --no-install-suggests --yes pipx python3 python-is-python3
ENV PATH="/root/.local/bin:${PATH}"
RUN pipx install poetry
RUN pipx inject poetry poetry-plugin-bundle
WORKDIR /src
COPY . .
RUN poetry bundle venv --only=main /venv

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /venv /venv
ENV SUPERNOTE_IP=
ENV SUPERNOTE_NAME=
ENV SYNC_INTERVAL=30
ENV SYNC_DIR=/supernote/sync
ENV TRASH_DIR=
ENV DB_URL="sqlite:////supernote/supernote-sync.db"
ENV NOTE_TO_PDF=true
ENV NOTE_TO_PDF_PAGE_SIZE=A5
ENV LOG_FILE="/supernote/supernote-sync.log"
ENV LOG_LEVEL=INFO
ENTRYPOINT ["/venv/bin/supernote-sync", "start"]
