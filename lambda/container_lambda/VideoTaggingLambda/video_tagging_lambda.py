#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
import subprocess
import boto3
from datetime import timedelta
from typing import Tuple, Dict, List
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

def format_timestamp(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS 格式"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# ----------------- 仅与 ffmpeg 输出相关的新增/修改开始 -----------------

def _run_cmd(cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    """运行子进程并返回 (returncode, stdout, stderr)，便于打印诊断信息"""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout or "", p.stderr or ""

def ffmpeg_available() -> bool:
    try:
        rc, out, err = _run_cmd(["ffmpeg", "-version"], timeout=5)
        return rc == 0
    except Exception:
        return False

def ffmpeg_has_libx264() -> bool:
    """检查 ffmpeg 是否支持 libx264 编码器（没有它就不可能输出 avc1/h264）"""
    if not ffmpeg_available():
        return False
    try:
        rc, out, err = _run_cmd(["ffmpeg", "-hide_banner", "-encoders"], timeout=10)
        if rc != 0:
            print(f"[WARN] ffmpeg -encoders failed, stderr:\n{err}")
            return False
        return "libx264" in out
    except Exception as e:
        print(f"[WARN] ffmpeg_has_libx264 exception: {e}")
        return False

def transcode_video_to_h264(input_video_path: str, output_video_path: str) -> bool:
    """
    fallback：把 mp4v 等视频转成 H.264(avc1) + yuv420p + faststart
    """
    if not ffmpeg_available():
        print("[ERROR] ffmpeg not available in this runtime. Cannot transcode to H.264.")
        return False

    if not ffmpeg_has_libx264():
        print("[ERROR] ffmpeg is available but does NOT include libx264 encoder. "
              "You must provide an ffmpeg build/layer with libx264. Cannot transcode to H.264.")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_video_path
    ]
    try:
        rc, out, err = _run_cmd(cmd, timeout=300)
        if rc != 0:
            print(f"[ERROR] Transcode to H.264 failed (rc={rc}). stderr:\n{err}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Transcode exception: {e}")
        return False

def merge_audio_to_video(video_path: str, audio_path: str, output_path: str) -> bool:
    """使用ffmpeg将音频合并到视频中（同时强制输出 H.264）"""
    if not ffmpeg_available():
        print("[ERROR] ffmpeg not available in this runtime. Skipping audio merge.")
        return False

    if not ffmpeg_has_libx264():
        print("[ERROR] ffmpeg is available but does NOT include libx264 encoder. "
              "You must provide an ffmpeg build/layer with libx264. Audio merge (H.264 output) cannot proceed.")
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,        # annotated temp（无音频）
        "-i", audio_path,        # 原视频（作为音频来源）
        "-map", "0:v:0",
        "-map", "1:a:0?",        # 可选音频（避免无音轨时报错）
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        output_path
    ]
    try:
        rc, out, err = _run_cmd(cmd, timeout=300)
        if rc != 0:
            print(f"[ERROR] Audio merge failed (rc={rc}). stderr:\n{err}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Audio merge exception: {e}")
        return False

# ----------------- 仅与 ffmpeg 输出相关的新增/修改结束 -----------------


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

def video_predict_with_annotations(
    video_path: str,
    output_path: str,
    confidence: float = 0.5
) -> Tuple[Dict, List]:

    video_info = sv.VideoInfo.from_video_path(video_path=video_path)
    fps = int(video_info.fps)
    class_dict = get_model().names

    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video：{video_path}")

    model = get_model()
    tracker = sv.ByteTrack(frame_rate=fps)

    box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    tracker_info = {}
    frame_count = 0
    time_records = []

    temp_output_path = output_path.replace('.mp4', '_temp.mp4')

    with sv.VideoSink(temp_output_path, video_info) as sink:
        unique_per_species = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_count / fps

            result = model(frame)[0]
            detections = sv.Detections.from_ultralytics(result)
            detections = tracker.update_with_detections(detections=detections)

            mask = detections.confidence > confidence
            detections = detections[mask]

            current_tracker_ids = set()

            if detections.tracker_id is not None:
                for trk_id, cls_id in zip(detections.tracker_id.tolist(), detections.class_id.tolist()):
                    trk_id = int(trk_id)
                    cls_id = int(cls_id)
                    species = class_dict[cls_id]
                    current_tracker_ids.add(trk_id)

                    unique_per_species.setdefault(species, set()).add(trk_id)

                    if trk_id not in tracker_info:
                        tracker_info[trk_id] = {
                            'species': species,
                            'start_frame': frame_count,
                            'start_time': current_time,
                            'last_seen_frame': frame_count
                        }
                    else:
                        tracker_info[trk_id]['last_seen_frame'] = frame_count

            disappeared_trackers = []
            for trk_id, info in tracker_info.items():
                if trk_id not in current_tracker_ids:
                    if frame_count - info['last_seen_frame'] > fps * 0.5:
                        disappeared_trackers.append(trk_id)

            for trk_id in disappeared_trackers:
                info = tracker_info[trk_id]
                end_time = info['last_seen_frame'] / fps
                time_records.append({
                    'species': info['species'],
                    'start': format_timestamp(info['start_time']),
                    'end': format_timestamp(end_time)
                })
                del tracker_info[trk_id]

            labels = []
            if detections.tracker_id is not None:
                for cls_id, conf in zip(detections.class_id.tolist(), detections.confidence.tolist()):
                    species = class_dict[int(cls_id)]
                    label = f"{species} {conf:.2f}"
                    labels.append(label)

            annotated_frame = box_annotator.annotate(scene=frame.copy(), detections=detections)
            annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)

            sink.write_frame(annotated_frame)
            frame_count += 1

        for trk_id, info in tracker_info.items():
            end_time = info['last_seen_frame'] / fps
            time_records.append({
                'species': info['species'],
                'start': format_timestamp(info['start_time']),
                'end': format_timestamp(end_time)
            })

    cap.release()

    time_records.sort(key=lambda x: x['start'])

    # 合并音频（如果可用）
    if os.path.exists(video_path):
        if merge_audio_to_video(temp_output_path, video_path, output_path):
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
        else:
            # ✅ 这里是关键：先尝试转码成 H.264
            if os.path.exists(temp_output_path):
                if transcode_video_to_h264(temp_output_path, output_path):
                    try:
                        os.remove(temp_output_path)
                    except OSError:
                        pass
                else:
                    # ❌ 不再静默 rename mp4v：直接保留 temp 并报错，方便你从日志定位原因
                    print("[ERROR] Both audio merge and H.264 transcode failed. "
                          "Leaving temp_output_path as-is (likely mp4v). "
                          "You need an ffmpeg build with libx264 in Lambda.")
                    # 如果你希望 Lambda 直接失败重试/报警，可以抛异常：
                    # raise RuntimeError("H.264 output not generated: ffmpeg/libx264 missing in Lambda")

                    # 若你一定要保留原行为（rename），把下面三行取消注释：
                    # if os.path.exists(output_path):
                    #     os.remove(output_path)
                    # os.rename(temp_output_path, output_path)

    counts = {species: len(ids) for species, ids in unique_per_species.items()}
    return counts, time_records


# ===== 主 handler =====
def handler(event, context):
    print(f"[DEBUG] Raw Event: {json.dumps(event)}")

    detail = event.get("detail", {})
    bucket = detail.get("bucket", {}).get("name")
    key    = detail.get("object", {}).get("key")

    if not bucket or not key:
        print("[ERROR] Missing bucket or key in event.detail")
        return {"statusCode": 400, "body": json.dumps({"error": "Missing bucket or key in event.detail"})}

    if not key.startswith("video/"):
        print(f"[INFO] Ignore non-video object: s3://{bucket}/{key}")
        return {"statusCode": 200, "body": json.dumps({"message": "Ignored non-video object"})}

    filename = os.path.basename(key)
    if "." in filename:
        file_id, ext = filename.rsplit(".", 1)
    else:
        file_id, ext = filename, "mp4"
    ext = ext or "mp4"

    tmp_video_path = f"/tmp/{file_id}.{ext}"
    tmp_annotated_video_path = f"/tmp/{file_id}_annotated.{ext}"

    try:
        s3_client.download_file(bucket, key, tmp_video_path)
        print(f"[INFO] S3 download complete: s3://{bucket}/{key} -> {tmp_video_path}")
    except ClientError as e:
        print(f"[ERROR] S3 download failed: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": f"S3 download failed: {e}"})}

    try:
        counts, time_records = video_predict_with_annotations(tmp_video_path, tmp_annotated_video_path, confidence=0.5)
        print(f"[INFO] model run complete: {counts}")
        print(f"[INFO] time records count: {len(time_records)}")
    except Exception as e:
        print(f"[ERROR] model run failed: {e}")
        import traceback
        traceback.print_exc()
        counts = {}
        time_records = []

    video_bucket_for_output = VIDEO_BUCKET_ENV or bucket
    annotated_video_key = f"tagging_output/{file_id}_annotated.{ext}"
    annotated_video_s3_url = None

    if os.path.exists(tmp_annotated_video_path):
        try:
            s3_client.upload_file(
                tmp_annotated_video_path,
                video_bucket_for_output,
                annotated_video_key,
                ExtraArgs={'ContentType': f'video/{ext}'}
            )
            print(f"[INFO] Annotated video uploaded: s3://{video_bucket_for_output}/{annotated_video_key}")

            video_bucket_for_url = VIDEO_BUCKET_ENV or bucket
            annotated_video_s3_url = f"https://{video_bucket_for_url}.s3.amazonaws.com/{annotated_video_key}"

            print(f"[INFO] Annotated video URL: {annotated_video_s3_url}")
            print(f"[DEBUG] Bucket: {video_bucket_for_url}, Region: {REGION}")
            print(f"[DEBUG] Annotated key: {annotated_video_key}")
            print(f"[DEBUG] Original video URL format: https://{video_bucket_for_url}.s3.amazonaws.com/{key}")
            print(f"[NOTE] If the file is not publicly accessible, ensure bucket policy allows public read for 'tagging_output/*' path")
        except ClientError as e:
            print(f"[ERROR] Failed to upload annotated video: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[WARN] Annotated video file not found: {tmp_annotated_video_path}")

    video_bucket_for_url = VIDEO_BUCKET_ENV or bucket
    s3_url = f"https://{video_bucket_for_url}.s3.amazonaws.com/{key}"

    thumbnail_key = f"thumbnail/{file_id}.jpg"
    try:
        s3_client.head_object(Bucket=THUMB_BUCKET, Key=thumbnail_key)
        thumbnail_url = f"https://{THUMB_BUCKET}.s3.amazonaws.com/{thumbnail_key}"
    except ClientError:
        thumbnail_url = ""

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tags_map = {species: {"N": str(cnt)} for species, cnt in counts.items()}

    timestemp_list = []
    for record in time_records:
        timestemp_list.append({
            "M": {
                "species": {"S": record["species"]},
                "start": {"S": record["start"]},
                "end": {"S": record["end"]}
            }
        })

    try:
        update_expression_parts = [
            "#S = :done",
            "file_type = :ft",
            "s3_url = :s",
            "tags = :tg",
            "upload_timestamp = :u",
            "tags_timestemp = :tt"
        ]
        expression_attribute_names = {"#S": "status"}
        expression_attribute_values = {
            ":done": {"S": "DONE"},
            ":ft":   {"S": "Video"},
            ":s":    {"S": s3_url},
            ":tg":   {"M": tags_map},
            ":u":    {"S": now_iso},
            ":tt":   {"L": timestemp_list},
        }

        if thumbnail_url:
            update_expression_parts.append("thumbnail_url = :t")
            expression_attribute_values[":t"] = {"S": thumbnail_url}

        if annotated_video_s3_url:
            update_expression_parts.append("annotated_output_url = :ao")
            expression_attribute_values[":ao"] = {"S": annotated_video_s3_url}

        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression="SET " + ", ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        print(
            f"[INFO] DynamoDB updated: file_id={file_id}, "
            f"file_type=Video, s3_url={s3_url}, tags={counts}, "
            f"timestemp_records={len(time_records)}, "
            f"annotated_output_url={annotated_video_s3_url}"
        )
    except ClientError as e:
        print(f"[ERROR] DynamoDB update failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    for tmp_file in [tmp_video_path, tmp_annotated_video_path]:
        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
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
                "annotated_video_url": annotated_video_s3_url,
                "timestemp_records_count": len(time_records),
            }
        ),
    }
