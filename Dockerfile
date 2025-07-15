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
ENV SUPERNOTE_URL=
ENV SUPERNOTE_DEVICE_NAME=
ENV SYNC_INTERVAL=60
ENV SYNC_DIR=/supernote/sync
ENV TRASH_DIR=/supernote/trash
ENV DB_URL="sqlite:////supernote/db.sqlite"
ENV CONVERT_TO_PDF=1
ENV PDF_PAGE_SIZE=A5
ENV PDF_VECTORIZE=0
ENV LOG_FILE="/supernote/sync.log"
ENV LOG_LEVEL=INFO
ENTRYPOINT ["/venv/bin/supernote-sync", "start"]
