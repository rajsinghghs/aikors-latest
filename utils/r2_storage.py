import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException
import uuid

def get_r2_client():
    """Cloudflare R2 ke liye boto3 client initialize karta hai"""
    return boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4'),
        region_name='auto'  # R2 requires region to be 'auto'
    )

def upload_file_to_r2(file_content: bytes, original_filename: str, folder: str, content_type: str):
    """
    R2 bucket mein file upload karta hai.
    folder: 'thumbnails' ya 'files'
    """
    try:
        client = get_r2_client()
        bucket_name = os.getenv('R2_BUCKET_NAME')
        public_domain = os.getenv('R2_PUBLIC_CUSTOM_DOMAIN')
        
        # File ka unique naam banayein taaki purani file overwrite na ho
        ext = original_filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        object_key = f"{folder}/{unique_filename}"
        
        # R2 par upload karein
        client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=content_type
        )
        
        # Agar thumbnail hai, toh public URL return karein
        if folder == "thumbnails" and public_domain:
            # e.g., https://pub-xxx.r2.dev/thumbnails/abc.jpg
            return f"{public_domain}/{object_key}"
        
        # Agar PDF/ZIP file hai, toh sirf R2 ka path (object_key) return karein (Secure)
        return object_key

    except ClientError as e:
        print(f"R2 Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Storage server error. Could not upload file.")

def generate_presigned_url(object_key: str, expiration: int = 3600):
    """
    Paid users ko PDF download karwane ke liye temporary secure link (1 ghante valid).
    """
    try:
        client = get_r2_client()
        bucket_name = os.getenv('R2_BUCKET_NAME')
        
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"Presigned URL Error: {e}")
        raise HTTPException(status_code=500, detail="Could not generate download link.")

# Yeh function file ke end mein add karein
def generate_presigned_upload_url(folder: str, original_filename: str, content_type: str):
    """Vercel 4.5MB Limit Bypass: Frontend se direct upload ke liye secure URL"""
    try:
        client = get_r2_client()
        bucket_name = os.getenv('R2_BUCKET_NAME')
        public_domain = os.getenv('R2_PUBLIC_CUSTOM_DOMAIN')
        
        ext = original_filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        object_key = f"{folder}/{unique_filename}"
        
        # Generate PUT URL
        url = client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ContentType': content_type
            },
            ExpiresIn=3600
        )
        
        file_url = object_key
        if folder == "thumbnails" and public_domain:
            file_url = f"{public_domain}/{object_key}"
            
        return {
            "upload_url": url,
            "file_url": file_url,
            "file_name": original_filename
        }
    except Exception as e:
        print(f"Generate Upload URL Error: {e}")
        raise HTTPException(status_code=500, detail="Could not generate direct upload link")        