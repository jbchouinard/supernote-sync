# supernote-sync

A python service for syncing files between [Supernote](https://supernote.com/) e-Ink notebooks and a local directory.

The service uses the [Supernote Browse & Access](https://support.supernote.com/Tools-Features/wi-fi-transfer) feature
to synchronize files. Files on the device cannot be deleted or overwritten using this feature.

`supernote-sync` syncs the INBOX directory in push mode, and all other directories in pull mode.

## Requirements
- Python 3.9+
- Poetry
