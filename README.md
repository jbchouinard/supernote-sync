# supernote-sync

An unofficial tool for [Supernote](https://supernote.com/) e-Ink notebooks, for syncing files locally.

The program uses the [Supernote Browse & Access](https://support.supernote.com/Tools-Features/wi-fi-transfer) feature to synchronize files. It must run on the same local network as the Supernote device.

By default, `supernote-sync` syncs the INBOX directory in push mode, and all other directories in pull mode.

## Requirements
- Python 3.9+
- Poetry

## Configuration

Configuration options can be set by environment variables or command line arguments.

### Supernote Connection Settings

| Option | Environment Variable | CLI Argument | Description | Default |
|--------|---------------------|-------------|-------------|--------|
| `supernote_url` | `SUPERNOTE_URL` | `--supernote-url` | URL of your Supernote device | *Required* |
| `supernote_device_name` | `SUPERNOTE_DEVICE_NAME` | `--supernote-device-name` | Name of your Supernote device | *Required* |

### Sync Settings

| Option | Environment Variable | CLI Argument | Description | Default |
|--------|---------------------|-------------|-------------|--------|
| `push_dirs` | `PUSH_DIRS` | `--push-dirs` | Directories to push files to (comma-separated) | `INBOX` |
| `pull_dirs` | `PULL_DIRS` | `--pull-dirs` | Directories to pull files from (comma-separated) | `Note,Document,MyStyle,EXPORT,SCREENSHOT` |
| `sync_extensions` | `SYNC_EXTENSIONS` | `--sync-extensions` | File extensions to sync (comma-separated) | `note,spd,spd-shm,spd-wal,pdf,epub,doc,txt,png,jpg,jpeg,webp` |
| `sync_interval` | `SYNC_INTERVAL` | `--sync-interval` | Sync interval in seconds | `60` |
| `sync_dir` | `SYNC_DIR` | `--sync-dir` | Local directory for synced files | `supernote/sync` |
| `trash_dir` | `TRASH_DIR` | `--trash-dir` | Local directory for deleted files - permanently deleted if unset | `supernote/trash` |

### Database Settings

| Option | Environment Variable | CLI Argument | Description | Default |
|--------|---------------------|-------------|-------------|--------|
| `db_url` | `DB_URL` | `--db-url` | Database connection URL | `sqlite:///supernote/db.sqlite` |

### PDF Conversion Settings

| Option | Environment Variable | CLI Argument | Description | Default |
|--------|---------------------|-------------|-------------|--------|
| `convert_to_pdf` | `CONVERT_TO_PDF` | `--convert-to-pdf` | Convert Supernote files to PDF | `False` |
| `force_reconvert` | `FORCE_RECONVERT` | `--force-reconvert` | Force reconversion of already converted files | `False` |
| `pdf_page_size` | `PDF_PAGE_SIZE` | `--pdf-page-size` | PDF page size | `A5` |
| `pdf_vectorize` | `PDF_VECTORIZE` | `--pdf-vectorize` | Vectorize notebooks when converting to PDF | `False` |

### Logging Settings

| Option | Environment Variable | CLI Argument | Description | Default |
|--------|---------------------|-------------|-------------|--------|
| `log_file` | `LOG_FILE` | `--log-file` | Log file path | None (logs to console) |
| `log_level` | `LOG_LEVEL` | `--log-level` | Logging level | `WARNING` |
