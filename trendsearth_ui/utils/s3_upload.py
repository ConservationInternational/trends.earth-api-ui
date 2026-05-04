"""Utility for uploading images to S3 for use in bulk email templates."""

import os
import uuid

import boto3

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def upload_image_to_s3(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload an image to S3 and return its public URL.

    Parameters
    ----------
    file_bytes:   Raw image bytes.
    filename:     Original filename (used to derive the file extension).
    content_type: MIME type, e.g. ``"image/jpeg"``.

    Returns
    -------
    str
        The public HTTPS URL of the uploaded object.

    Raises
    ------
    ValueError
        If ``content_type`` is not an allowed image type or the file exceeds 5 MB.
    """
    if content_type not in _ALLOWED_TYPES:
        raise ValueError(f"Unsupported image type: {content_type!r}")
    if len(file_bytes) > _MAX_BYTES:
        raise ValueError("Image exceeds 5 MB limit")

    bucket = os.environ.get("S3_BUCKET", "trends.earth")
    prefix = os.environ.get("S3_EMAIL_IMAGE_PREFIX", "email-images").rstrip("/")
    region = os.environ.get("AWS_REGION", "us-east-1")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    key = f"{prefix}/{uuid.uuid4()}.{ext}"

    s3 = boto3.client("s3", region_name=region)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ACL="public-read",
        ContentType=content_type,
    )

    return f"https://s3.dualstack.{region}.amazonaws.com/{bucket}/{key}"
