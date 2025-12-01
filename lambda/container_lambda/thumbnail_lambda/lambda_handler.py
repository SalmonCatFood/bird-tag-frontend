#!/usr/bin/env python
# coding: utf-8

import os
import json
import boto3
import cv2 as cv
from botocore.exceptions import ClientError

REGION         = os.getenv("AWS_REGION", "ap-southeast-2")
IMAGES_BUCKET  = os.getenv("IMAGES_S3")          # 可选，用于区分不同 bucket
VIDEO_BUCKET   = os.getenv("VIDEO_S3")
THUMB_BUCKET   = os.getenv("THUMBNAILS_S3")
METADATA_TABLE = os.getenv("METADATA_TABLE")

s3_client  = boto3.client("s3", region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)


def generate_image_thumbnail(source_path: str, dest_path: str, max_width: int = 200):
    img = cv.imread(source_path)
    if img is None:
        raise RuntimeError(f"Cannot read image: {source_path}")
    h, w = img.shape[:2]
    if w <= max_width:
        cv.imwrite(dest_path, img, [int(cv.IMWRITE_JPEG_QUALITY), 85])
        return
    scale = max_width / float(w)
    new_dim = (max_width, int(h * scale))
    resized = cv.resize(img, new_dim, interpolation=cv.INTER_AREA)
    cv.imwrite(dest_path, resized, [int(cv.IMWRITE_JPEG_QUALITY), 85])


def generate_video_thumbnail(source_path: str, dest_path: str, max_width: int = 200):
    cap = cv.VideoCapture(source_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {source_path}")
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError(f"Cannot read the first frame: {source_path}")
    h, w = frame.shape[:2]
    if w <= max_width:
        cv.imwrite(dest_path, frame, [int(cv.IMWRITE_JPEG_QUALITY), 85])
        return
    scale = max_width / float(w)
    new_dim = (max_width, int(h * scale))
    resized = cv.resize(frame, new_dim, interpolation=cv.INTER_AREA)
    cv.imwrite(dest_path, resized, [int(cv.IMWRITE_JPEG_QUALITY), 85])


def handler(event, context):
    print(f"[DEBUG] Raw EventBridge event: {json.dumps(event)}")

    # 这里假定一定是 EventBridge 转发的 S3 Object Created 事件
    # 结构类似：
    # {
    #   "source": "aws.s3",
    #   "detail-type": "Object Created",
    #   "detail": {
    #       "bucket": {"name": "weihanxu-birdtag-image-s3"},
    #       "object": {"key": "image/xxx.jpg", ...}
    #   }
    # }
    if event.get("source") != "aws.s3" or "detail" not in event:
        print(f"[ERROR] unexpected event source or missing detail: {event}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid EventBridge S3 event"})
        }

    detail = event["detail"]
    bucket = detail.get("bucket", {}).get("name")
    key    = detail.get("object", {}).get("key")

    if not bucket or not key:
        print(f"[ERROR] Missing bucket/key in detail: {event}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing bucket or key in event.detail"})
        }

    basename = os.path.basename(key)          # e.g. unknown_user_xxx.jpg
    file_id, _ = os.path.splitext(basename)   # 去掉扩展名

    print(f"[INFO] Parsed from EventBridge: bucket={bucket}, key={key}, file_id={file_id}")

    dirname = os.path.dirname(key)            # "image" or "video"
    if dirname not in ("image", "video"):
        print(f"[INFO] prefix not image/ or video/, ignore: {key}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Ignored prefix"})
        }

    _, ext = os.path.splitext(key)
    ext = ext.lstrip(".") or "jpg"
    tmp_src   = f"/tmp/{file_id}.{ext}"
    tmp_thumb = f"/tmp/{file_id}.jpg"

    # 从 S3 下载源文件（内部网络）
    try:
        s3_client.download_file(bucket, key, tmp_src)
        print(f"[INFO] S3 downloaded: s3://{bucket}/{key} -> {tmp_src}")
    except ClientError as e:
        print(f"[ERROR] failed to download: bucket={bucket}, key={key}, error={e}")
        raise

    # 生成缩略图
    try:
        if dirname == "image":
            generate_image_thumbnail(tmp_src, tmp_thumb)
        else:
            generate_video_thumbnail(tmp_src, tmp_thumb)
        print(f"[INFO] thumbnail generated at {tmp_thumb}")
    except Exception as e:
        print(f"[ERROR] failed to generate thumbnail: {e}")
        try:
            os.remove(tmp_src)
        except OSError:
            pass
        raise

    # 上传缩略图到 THUMB_BUCKET
    thumb_key = f"thumbnails/{file_id}.jpg"
    try:
        s3_client.upload_file(
            tmp_thumb, THUMB_BUCKET, thumb_key,
            ExtraArgs={"ContentType": "image/jpeg"}
        )
        print(f"[INFO] thumbnail uploaded: s3://{THUMB_BUCKET}/{thumb_key}")
    except ClientError as e:
        print(f"[ERROR] s3 upload failed: {e}")
        try:
            os.remove(tmp_src)
        except OSError:
            pass
        try:
            os.remove(tmp_thumb)
        except OSError:
            pass
        raise

    thumbnail_url = f"https://{THUMB_BUCKET}.s3.amazonaws.com/{thumb_key}"

    # 更新 DynamoDB
    try:
        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression="SET thumbnail_url = :t",
            ExpressionAttributeValues={":t": {"S": thumbnail_url}}
        )
        print(f"[INFO] update DynamoDB thumbnail_url: {file_id} -> {thumbnail_url}")
    except ClientError as e:
        print(f"[ERROR] DynamoDB update thumbnail_url failed: {e}")
        # 可以根据需要决定是否 raise，这里先不抛出去
        pass

    # 清理临时文件
    for path in (tmp_src, tmp_thumb):
        try:
            os.remove(path)
        except OSError:
            pass

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Thumbnail generated for {file_id}",
            "file_id": file_id,
            "thumbnail_url": thumbnail_url
        })
    }
