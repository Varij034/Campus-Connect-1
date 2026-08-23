import os
import cloudinary
import cloudinary.uploader
import logging
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

logger = logging.getLogger(__name__)

# Configure Cloudinary if credentials are provided
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    logger.info("Cloudinary configured successfully.")
else:
    logger.warning("Cloudinary credentials are not fully set. File uploads to cloud will fail.")


def upload_resume_to_cloudinary(file_path: str, public_id: str = None) -> str:
    """
    Upload a file to Cloudinary and return the secure URL.
    Returns empty string if upload fails.
    """
    if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
        logger.error("Cloudinary is not configured.")
        return ""
        
    try:
        # Use raw resource type for PDFs and docs
        response = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type="raw",
            folder="resumes"
        )
        return response.get("secure_url", "")
    except Exception as e:
        logger.error(f"Failed to upload to Cloudinary: {e}")
        return ""
