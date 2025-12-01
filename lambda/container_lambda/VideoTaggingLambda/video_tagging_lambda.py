#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
import boto3
from botocore.exceptions import ClientError
from ultralytics import YOLO
import supervision as sv
import cv2 as cv

# ===== 配置 =====
REGION         = os.getenv("AWS_REGION", "ap-southeast-2")
VIDEO_BUCKET_ENV = os.getenv("VIDEO_S3")      # 可选：如果你希望 s3_url 固定用某个 bucket
THUMB_BUCKET   = os.getenv("THUMBNAILS_S3")
METADATA_TABLE = os.getenv("METADATA_TABLE")
MODEL_PATH     = os.getenv("MODEL_PATH", "/opt/model.pt")

s3_client  = boto3.client("s3", region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)

# ===== YOLO 模型懒加载 =====
_model = None
def get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model

def video_predict_unique_counts(video_path: str, confidence: float = 0.5) -> dict:
    video_info = sv.VideoInfo.from_video_path(video_path=video_path)
    fps = int(video_info.fps)
    class_dict = get_model().names

    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video：{video_path}")

    model   = get_model()
    tracker = sv.ByteTrack(frame_rate=fps)
    unique_per_species = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result     = model(frame)[0]
        detections = sv.Detections.from_ultralytics(result)
        detections = tracker.update_with_detections(detections=detections)
        if detections.tracker_id is None:
            continue
        mask       = detections.confidence > confidence
        detections = detections[mask]
        for trk_id, cls_id in zip(detections.tracker_id.tolist(), detections.class_id.tolist()):
            species = class_dict[int(cls_id)]
            unique_per_species.setdefault(species, set()).add(int(trk_id))

    cap.release()
    return {species: len(ids) for species, ids in unique_per_species.items()}

# ===== 主 handler =====
def handler(event, context):
    """
    期望事件来源：
    - EventBridge 规则：source = "aws.s3", detail-type = "Object Created"
    - event["detail"]["bucket"]["name"] 为 bucket
    - event["detail"]["object"]["key"] 为对象 key，例如 "video/xxx.mp4"
    """
    print(f"[DEBUG] Raw Event: {json.dumps(event)}")

    # 从 EventBridge S3 事件中取 bucket / key
    detail = event.get("detail", {})
    bucket = detail.get("bucket", {}).get("name")
    key    = detail.get("object", {}).get("key")

    if not bucket or not key:
        print("[ERROR] Missing bucket or key in event.detail")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing bucket or key in event.detail"})
        }

    # 只处理 video/ 前缀的对象（与你的 EventBridge 规则保持一致，也做一次保护）
    if not key.startswith("video/"):
        print(f"[INFO] Ignore non-video object: s3://{bucket}/{key}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Ignored non-video object"})
        }

    # 从 key 中解析 file_id 和扩展名
    # 例如 key = "video/abcd-1234.mp4"
    filename = os.path.basename(key)         # "abcd-1234.mp4"
    if "." in filename:
        file_id, ext = filename.rsplit(".", 1)
    else:
        file_id, ext = filename, "mp4"
    ext = ext or "mp4"

    tmp_video_path = f"/tmp/{file_id}.{ext}"

    # ===== 从 S3 下载视频（走 AWS 内部网络，不用 presigned url）=====
    try:
        s3_client.download_file(bucket, key, tmp_video_path)
        print(f"[INFO] S3 download complete: s3://{bucket}/{key} -> {tmp_video_path}")
    except ClientError as e:
        print(f"[ERROR] S3 download failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"S3 download failed: {e}"}),
        }

    # ===== 模型推理 =====
    try:
        counts = video_predict_unique_counts(tmp_video_path, confidence=0.5)
        print(f"[INFO] model run complete: {counts}")
    except Exception as e:
        print(f"[ERROR] model run failed: {e}")
        counts = {}

    # ===== 构造对外可访问的 s3_url =====
    # 如果设置了 VIDEO_S3 环境变量就用它，否则用事件里的 bucket
    video_bucket_for_url = VIDEO_BUCKET_ENV or bucket
    s3_url = f"https://{video_bucket_for_url}.s3.amazonaws.com/{key}"

    # ===== 检查缩略图是否存在 =====
    thumbnail_key = f"thumbnail/{file_id}.jpg"
    try:
        s3_client.head_object(Bucket=THUMB_BUCKET, Key=thumbnail_key)
        thumbnail_url = f"https://{THUMB_BUCKET}.s3.amazonaws.com/{thumbnail_key}"
    except ClientError:
        thumbnail_url = ""

    # ===== 写入 / 更新 DynamoDB =====
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tags_map = {species: {"N": str(cnt)} for species, cnt in counts.items()}

    try:
        update_expression_parts = [
            "#S = :done",
            "file_type = :ft",
            "s3_url = :s",
            "tags = :tg",
            "upload_timestamp = :u"
        ]
        expression_attribute_names = {"#S": "status"}
        expression_attribute_values = {
            ":done": {"S": "DONE"},
            ":ft":   {"S": "Video"},
            ":s":    {"S": s3_url},
            ":tg":   {"M": tags_map},
            ":u":    {"S": now_iso},
        }

        if thumbnail_url:
            update_expression_parts.append("thumbnail_url = :t")
            expression_attribute_values[":t"] = {"S": thumbnail_url}

        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression="SET " + ", ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        print(
            f"[INFO] DynamoDB updated: file_id={file_id}, "
            f"file_type=Video, s3_url={s3_url}, tags={counts}"
        )
    except ClientError as e:
        print(f"[ERROR] DynamoDB update failed: {e}")
        # 根据需要决定是否要抛出异常让 Lambda 失败重试
        raise

    # ===== 清理临时文件 =====
    try:
        os.remove(tmp_video_path)
    except OSError:
        pass

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"Processed video {file_id}",
                "file_id": file_id,
                "bucket": bucket,
                "key": key,
                "tags": counts,
            }
        ),
    }