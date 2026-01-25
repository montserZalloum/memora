import json
import boto3
import frappe
import requests
from botocore.config import Config

def get_cdn_client(settings):
    """Get S3-compatible client for either AWS S3 or Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.get_password('access_key'),
        aws_secret_access_key=settings.get_password('secret_key'),
        config=Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
    )

def test_connection():
    """Test connection to CDN and bucket."""
    settings = frappe.get_single("CDN Settings")
    if not settings.enabled:
        return {'status': 'disabled'}

    try:
        client = get_cdn_client(settings)
        client.head_bucket(Bucket=settings.bucket_name)
        return {'status': 'success', 'bucket': settings.bucket_name}
    except Exception as e:
        frappe.log_error("CDN Connection Test Failed", str(e))
        return {'status': 'error', 'message': str(e)}


def purge_cdn_cache(zone_id, api_token, file_urls):
    """Purge specific files from Cloudflare cache."""
    response = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        json={"files": file_urls}  # Max 30 URLs per request
    )
    return response.json()

def get_versioned_url(base_url, version_timestamp):
    """Generate cache-busting URL."""
    return f"{base_url}?v={version_timestamp}"

def generate_signed_url(client, bucket, key, expiry_seconds=14400):
    """Generate 4-hour signed URL for sensitive content."""
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expiry_seconds
    )

def upload_json(client, bucket, key, data):
    """Upload JSON with proper content type and cache control."""
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json; charset=utf-8',
            CacheControl='public, max-age=300'  # 5 min cache, invalidated on update
        )
        return True, None, None
    except Exception as e:
        frappe.log_error(f"Failed to upload JSON to {key}: {str(e)}", "CDN Upload Failed")
        return False, str(e), None


def upload_json_from_file(client, bucket, key, file_path):
    """Upload JSON from local file path with proper content type and cache control.
    
    Args:
        client: S3 client instance
        bucket (str): Bucket name
        key (str): Object key (path in bucket)
        file_path (str): Absolute path to local file to upload
    
    Returns:
        tuple: (success, error_message, etag)
            - success (bool): True if upload succeeded
            - error_message (str | None): Error message if failed, None if successful
            - etag (str | None): ETag from CDN response for hash verification
    """
    try:
        with open(file_path, 'rb') as f:
            response = client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f.read(),
                ContentType='application/json; charset=utf-8',
                CacheControl='public, max-age=300'  # 5 min cache, invalidated on update
            )
        etag = response.get('ETag', '').strip('"')
        return True, None, etag
    except FileNotFoundError:
        frappe.log_error(f"Local file not found for upload: {file_path}", "CDN Upload Failed")
        return False, f"Local file not found: {file_path}", None
    except Exception as e:
        frappe.log_error(f"Failed to upload JSON from file {file_path} to {key}: {str(e)}", "CDN Upload Failed")
        return False, str(e), None

def delete_json(client, bucket, key):
    """Delete a JSON file from CDN."""
    try:
        client.delete_object(Bucket=bucket, Key=key)
        return True, None
    except client.exceptions.NoSuchKey:
        # File doesn't exist, that's fine
        return True, None
    except Exception as e:
        frappe.log_error(f"Failed to delete JSON {key}: {str(e)}", "CDN Delete Failed")
        return False, str(e)

def delete_folder(client, bucket, prefix):
    """
    Delete all objects with a given prefix (folder-like structure).

    Args:
        client: S3 client instance
        bucket (str): Bucket name
        prefix (str): Prefix to delete (e.g., 'plans/my-plan/')

    Returns:
        tuple: (success_count, error_count, errors)
    """
    success_count = 0
    error_count = 0
    errors = []

    try:
        # List all objects with the prefix
        paginator = client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

        objects_to_delete = []
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})

        # Delete in batches (max 1000 objects per request)
        for i in range(0, len(objects_to_delete), 1000):
            batch = objects_to_delete[i:i+1000]
            try:
                response = client.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': batch}
                )

                # Count successes
                if 'Deleted' in response:
                    success_count += len(response['Deleted'])

                # Count errors
                if 'Errors' in response:
                    error_count += len(response['Errors'])
                    for error in response['Errors']:
                        errors.append(f"{error['Key']}: {error['Message']}")

            except Exception as e:
                error_count += len(batch)
                errors.append(f"Batch {i}-{i+999}: {str(e)}")

        return success_count, error_count, errors

    except Exception as e:
        frappe.log_error(f"Failed to delete folder {prefix}: {str(e)}", "CDN Delete Folder Failed")
        return 0, len(objects_to_delete) if 'objects_to_delete' in locals() else 0, [str(e)]

def upload_plan_files(client, bucket, plan_name, files_data):
    """
    Upload all files for a plan and return uploaded URLs for cache purging.

    Args:
        client: S3 client instance
        bucket (str): Bucket name
        plan_name (str): Plan document name
        files_data (dict): Dictionary of {path: data} from json_generator

    Returns:
        tuple: (uploaded_urls, errors)
    """
    uploaded_urls = []
    errors = []

    for path, data in files_data.items():
        success, error, _ = upload_json(client, bucket, path, data)
        if success:
            # Generate full CDN URL for cache purging
            settings = frappe.get_single("CDN Settings")
            full_url = f"{settings.cdn_base_url}/{path}"
            uploaded_urls.append(full_url)
        else:
            errors.append(f"{path}: {error}")

    return uploaded_urls, errors


def upload_plan_files_from_local(client, bucket, plan_name, files_info):
    """
    Upload files from local storage for a plan and return upload results.

    Args:
        client: S3 client instance
        bucket (str): Bucket name
        plan_name (str): Plan document name
        files_info (dict): Dictionary of {path: {"local_path": str, "data": dict}}

    Returns:
        tuple: (uploaded_urls, upload_results, errors)
            - uploaded_urls (list): List of full CDN URLs for cache purging
            - upload_results (dict): Dictionary of {path: {"success": bool, "etag": str, "error": str | None}}
            - errors (list): List of error messages
    """
    uploaded_urls = []
    upload_results = {}
    errors = []

    from memora.services.cdn_export.local_storage import get_local_base_path

    for path, info in files_info.items():
        local_path = info.get("local_path")
        
        if local_path:
            # Upload from local file
            success, error, etag = upload_json_from_file(client, bucket, path, local_path)
            upload_results[path] = {
                "success": success,
                "etag": etag,
                "error": error,
                "local_path": local_path
            }
        else:
            # Fallback to in-memory upload
            success, error, _ = upload_json(client, bucket, path, info.get("data", {}))
            upload_results[path] = {
                "success": success,
                "etag": None,
                "error": error,
                "local_path": None
            }

        if success:
            # Generate full CDN URL for cache purging
            settings = frappe.get_single("CDN Settings")
            full_url = f"{settings.cdn_base_url}/{path}"
            uploaded_urls.append(full_url)
        else:
            errors.append(f"{path}: {error}")

    return uploaded_urls, upload_results, errors

def get_cdn_base_url(settings):
    """Get the base URL for CDN content."""
    if not settings.cdn_base_url:
        # If no CDN base URL is set, construct from bucket and endpoint
        bucket_domain = settings.bucket_name
        if settings.endpoint_url:
            # Extract domain from endpoint URL
            if settings.endpoint_url.startswith('https://'):
                bucket_domain = settings.bucket_name + '.' + settings.endpoint_url.split('//')[1].split('/')[0]
        return f"https://{bucket_domain}"
    return settings.cdn_base_url.rstrip('/')

def delete_plan_folder(settings, plan_id):
    """
    Delete entire plan folder from CDN.

    Args:
        settings: CDN Settings document
        plan_id (str): Plan document name

    Returns:
        tuple: (success_count, error_count, errors)
    """
    client = get_cdn_client(settings)
    prefix = f"plans/{plan_id}/"
    return delete_folder(client, settings.bucket_name, prefix)
