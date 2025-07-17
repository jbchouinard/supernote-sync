# supernote-sync

An unofficial tool for [Supernote](https://supernote.com/) e-Ink notebooks, to automatically backup files from the Supernote
using local WiFi.

I have it running on my home TrueNAS server to automatically backup my notes and drawings.

## Features
- Local network only, no cloud
- Optional conversion to standard formats (NOTE to PDF, SPD to PNG)
- Pull mode to download files from the Supernote
- Push mode to upload files to the Supernote (for INBOX folder)
- Usable as a CLI tool or service / daemon

`supernote-sync` uses the [Supernote Browse & Access](https://support.supernote.com/Tools-Features/wi-fi-transfer) feature to synchronize files.
The computer and notebook must be on the same network, and WiFi transfer must be toggled on in the Supernote settings.

By default, the INBOX folder is configured in Push mode, and all the other folders are configured in Pull mode.

Push mode is limited, and full bi-directional sync is not really practical, because the WiFi transfer function of the Supernote
does not allow deleting or overwriting files on the device.

## Run locally

### Install with pipx

```sh
pipx install supernote-sync
```

### Run once

You can find the IP address of your Supernote in the popup when turning on WiFi transfer.


```sh
supernote-sync --ip xxx.xxx.xxx.xxx --name="My Device Name" --sync-dir=./supernote run
```

### Start daemon

```sh
supernote-sync --ip xxx.xxx.xxx.xxx --name="My Device Name" --sync-dir=./supernote start
```

## Run with Docker

The Docker image is configured to use the /supernote path inside the container. Mount a volume to /supernote to write the files
to the host system.

The container can be configured via environment variables (see below).

```sh
docker run \ 
    -e SUPERNOTE_IP="xxx.xxx.xxx.xxx" \
    -e SUPERNOTE_NAME="My Device Name" \
    -v /path/to/supernote:/supernote \
    ghcr.io/jbchouinard/supernote-sync:latest
```

## Configuration

Configuration options can be set by environment variables or command line arguments.

### Supernote Connection Settings

WiFi transfer must be toggled on on the Supernote device. The popup will show the IP address of the device.

| Option | Environment Variable | CLI Argument | Description                         | Default    |
|--------|----------------------|--------------|-------------------------------------|------------|
| `ip`   | `SUPERNOTE_IP`       | `--ip`       | IP address of your Supernote device | *Required* |
| `port` | `SUPERNOTE_PORT`     | `--port`     | Port of your Supernote device       | 8089       |
| `name` | `SUPERNOTE_NAME`     | `--name`     | Name of your Supernote device       | *Required* |

### File Sync Settings

| Option            | Environment Variable | CLI Argument        | Description                                    | Default                                                       |
|-------------------|----------------------|---------------------|------------------------------------------------|---------------------------------------------------------------|
| `push_dirs`       | `PUSH_DIRS`          | `--push-dirs`       | Folders to download files to (comma-separated) | `INBOX`                                                       |
| `pull_dirs`       | `PULL_DIRS`          | `--pull-dirs`       | Folders to upload files from (comma-separated) | `Note,Document,MyStyle,EXPORT,SCREENSHOT`                     |
| `sync_extensions` | `SYNC_EXTENSIONS`    | `--sync-extensions` | File extensions to sync (comma-separated)      | `note,spd,spd-shm,spd-wal,pdf,epub,doc,txt,png,jpg,jpeg,webp` |
| `sync_interval`   | `SYNC_INTERVAL`      | `--sync-interval`   | Sync interval in seconds                       | `60`                                                          |
| `sync_dir`        | `SYNC_DIR`           | `--sync-dir`        | Local folder to sync to                        | `supernote/sync`                                              |
| `trash_dir`       | `TRASH_DIR`          | `--trash-dir`       | Move files instead of deleting them            | *Delete permanently*                                          |

### Database Settings

By default, uses a local SQLite database. Any database supported by SQLAlchemy should work. Tested with SQLite and PostgreSQL.

| Option   | Environment Variable | CLI Argument | Description             | Default                         |
|----------|----------------------|--------------|-------------------------|---------------------------------|
| `db_url` | `DB_URL`             | `--db-url`   | Database connection URL | `sqlite:///supernote/db.sqlite` |

### Note to PDF Conversion Settings

Configure automatic conversion of notebooks to PDF when syncing.

To match the notebook scale, the page size is A5 for the Manta, or A6 for the Nomad.

| Option                  | Environment Variable    | CLI Argument              | Description                                      | Default |
|-------------------------|-------------------------|---------------------------|--------------------------------------------------|---------|
| `note_to_pdf`           | `NOTE_TO_PDF`           | `--note-to-pdf`           | Convert Supernote .note files to PDF on download | `True`  |
| `note_to_pdf_reconvert` | `NOTE_TO_PDF_RECONVERT` | `--note-to-pdf-reconvert` | Force reconversion of already converted files    | `False` |
| `note_to_pdf_page_size` | `NOTE_TO_PDF_PAGE_SIZE` | `--note-to-pdf-page-size` | Output page size of PDF                          | `A5`    |
| `note_to_pdf_vectorize` | `NOTE_TO_PDF_VECTORIZE` | `--note-to-pdf-vectorize` | Vectorize content when converting to PDF         | `False` |

### SPD to PNG Conversion Settings

Configure automatic conversion of SPD files to PNG when syncing.

| Option                 | Environment Variable   | CLI Argument             | Description                                             | Default |
|------------------------|------------------------|--------------------------|---------------------------------------------------------|---------|
| `spd_to_png`           | `SPD_TO_PNG`           | `--spd-to-png`           | Convert Supernote Atelier .spd files to PNG on donwload | `True`  |
| `spd_to_png_reconvert` | `SPD_TO_PNG_RECONVERT` | `--spd-to-png-reconvert` | Force reconversion of already converted files           | `False` |

### Logging Settings

| Option      | Environment Variable | CLI Argument  | Description                                                                        | Default  |
|-------------|----------------------|---------------|------------------------------------------------------------------------------------|----------|
| `log_file`  | `LOG_FILE`           | `--log-file`  | Log file path, or `stdout`/`stderr`                                                | `stdout` |
| `log_level` | `LOG_LEVEL`          | `--log-level` | Logging level: `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL` | `INFO`   |

## Development

### Install dependencies

```sh
poetry install
```

### Run with Poetry

```sh
poetry run supernote-sync start
```

### Build Docker image

```sh
docker build -t supernote-sync .
```
