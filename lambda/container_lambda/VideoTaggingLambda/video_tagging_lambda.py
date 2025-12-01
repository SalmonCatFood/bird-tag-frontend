#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
import boto3
import tempfile
import requests
from botocore.exceptions import ClientError
from ultralytics import YOLO
import supervision as sv
import cv2 as cv


REGION         = os.getenv("AWS_REGION", "ap-southeast-2")
VIDEO_BUCKET   = os.getenv("VIDEO_S3")
THUMB_BUCKET   = os.getenv("THUMBNAILS_S3")
METADATA_TABLE = os.getenv("METADATA_TABLE")
MODEL_PATH     = os.getenv("MODEL_PATH", "/opt/model.pt")


s3_client  = boto3.client("s3", region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)

# 模型加载（冷启动）
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

def handler(event, context):
    # 1. 校验 payload
    if "file_id" not in event or "presigned_url" not in event:
        print("[ERROR] event missed file_id 或 presigned_url")
        return {"statusCode": 400, "body": json.dumps({"error":"Missing file_id or presigned_url"})}

    file_id       = event["file_id"]
    presigned_url = event["presigned_url"]

    tmp_video_path = f"/tmp/{file_id}.mp4"
    try:
        with requests.get(presigned_url, stream=True) as r:
            r.raise_for_status()
            with open(tmp_video_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        print(f"[INFO] Donwloading to {tmp_video_path}")
    except Exception as e:
        print(f"[ERROR] failed to download: {e}")
        raise

    try:
        counts = video_predict_unique_counts(tmp_video_path, confidence=0.5)
        print(f"[INFO] model counts={counts}")
    except Exception as e:
        print(f"[ERROR] model run failed: {e}")
        counts = {}


    s3_url        = f"https://{VIDEO_BUCKET}.s3.amazonaws.com/video/{file_id}.mp4"
    thumbnail_key = f"thumbnails/{file_id}.jpg"
    try:
        s3_client.head_object(Bucket=THUMB_BUCKET, Key=thumbnail_key)
        thumbnail_url = f"https://{THUMB_BUCKET}.s3.amazonaws.com/{thumbnail_key}"
    except ClientError:
        thumbnail_url = ""

    # 5. 构造更新表达式
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tags_map = { sp: {"N": str(cnt)} for sp, cnt in counts.items() }

    update_parts = [
        "#S = :done",
        "s3_url = :s",
        "tags = :tg",
        "upload_timestamp = :u"
    ]
    expr_attr_names  = {"#S": "status"}
    expr_attr_values = {
        ":done": {"S": "DONE"},
        ":s":    {"S": s3_url},
        ":tg":   {"M": tags_map},
        ":u":    {"S": now_iso}
    }


    if thumbnail_url:
        update_parts.append("thumbnail_url = :t")
        expr_attr_values[":t"] = {"S": thumbnail_url}

    update_expression = "SET " + ", ".join(update_parts)


    try:
        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        print(f"[INFO] updated DynamoDB: file_id={file_id}, tags={counts}")
    except ClientError as e:
        print(f"[ERROR] update DynamoDB failed: {e}")
        raise


    try:
        os.remove(tmp_video_path)
    except:
        pass

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Processed video {file_id}", "tags": counts})
    }