from fastapi import UploadFile
from typing import List, Optional
import os
from src.utils.error_handling import FileUploadError, ERROR_MESSAGES

# Allowed file types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

# Maximum file size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

def validate_file(
    file: UploadFile,
    allowed_types: Optional[dict] = None,
    max_size: Optional[int] = None
) -> None:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        allowed_types: Dictionary of allowed MIME types and their extensions
        max_size: Maximum file size in bytes
    
    Raises:
        FileUploadError: If validation fails
    """
    if not file:
        raise FileUploadError(ERROR_MESSAGES["file_upload"]["upload_failed"])
    
    # Use default values if not provided
    allowed_types = allowed_types or ALLOWED_IMAGE_TYPES
    max_size = max_size or MAX_FILE_SIZE
    
    # Check file type
    if file.content_type not in allowed_types:
        raise FileUploadError(
            ERROR_MESSAGES["file_upload"]["invalid_type"],
            details={"allowed_types": list(allowed_types.keys())}
        )
    
    # Check file size
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_size:
            raise FileUploadError(
                ERROR_MESSAGES["file_upload"]["too_large"],
                details={"max_size": max_size}
            )
    
    # Reset file pointer
    file.file.seek(0)

def get_file_extension(content_type: str) -> str:
    """
    Get file extension from content type
    
    Args:
        content_type: MIME type of the file
    
    Returns:
        str: File extension with dot
    """
    return ALLOWED_IMAGE_TYPES.get(content_type, "")

def is_valid_image_type(content_type: str) -> bool:
    """
    Check if content type is a valid image type
    
    Args:
        content_type: MIME type to check
    
    Returns:
        bool: True if valid image type
    """
    return content_type in ALLOWED_IMAGE_TYPES 