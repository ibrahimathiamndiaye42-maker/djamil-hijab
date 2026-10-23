import os, uuid
from flask import current_app

ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def save_image(file_storage, folder="products"):
    ext = ALLOWED.get(file_storage.mimetype)
    if not ext:
        from ..errors import ApiError
        raise ApiError("Format d'image non supporté (JPG, PNG ou WebP)")
    key = f"{folder}/{uuid.uuid4().hex}{ext}"
    cfg = current_app.config
    if cfg["STORAGE_BACKEND"] == "s3":
        import boto3
        s3 = boto3.client("s3", endpoint_url=cfg["S3_ENDPOINT_URL"], aws_access_key_id=cfg["S3_ACCESS_KEY"],
                          aws_secret_access_key=cfg["S3_SECRET_KEY"], region_name=cfg["S3_REGION"])
        s3.upload_fileobj(file_storage.stream, cfg["S3_BUCKET"], key, ExtraArgs={"ContentType": file_storage.mimetype})
        return f"{cfg['S3_PUBLIC_BASE_URL'].rstrip('/')}/{key}"
    path = os.path.join(cfg["UPLOAD_DIR"], key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file_storage.save(path)
    return f"/files/{key}"
