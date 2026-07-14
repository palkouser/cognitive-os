"""Content-addressed artifact adapters."""

from .filesystem import ContentAddressedFilesystem, StoredBlob

__all__ = ["ContentAddressedFilesystem", "StoredBlob"]
