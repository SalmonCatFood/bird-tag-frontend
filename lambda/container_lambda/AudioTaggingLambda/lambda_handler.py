import os
import json
import time
import boto3
from botocore.exceptions import ClientError
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
from datetime import timedelta

# ===== 配置 =====
REGION         = os.getenv("AWS_REGION", "ap-southeast-2")
AUDIO_BUCKET_ENV = os.getenv("AUDIO_S3")      # 可选：如果你希望 s3_url 固定用某个 bucket
METADATA_TABLE = os.getenv("METADATA_TABLE")
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.3"))

s3_client  = boto3.client("s3", region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)

# ===== BirdNET 分析器懒加载 =====
_analyzer = None
def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = Analyzer()
    return _analyzer

def format_timestamp(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS 格式"""
    td = timedelta(seconds=seconds)
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# ===== 主 handler =====
def handler(event, context):
    """
    期望事件来源：
    - EventBridge 规则：source = "aws.s3", detail-type = "Object Created"
    - event["detail"]["bucket"]["name"] 为 bucket
    - event["detail"]["object"]["key"] 为对象 key，例如 "audio/xxx.mp3"
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

    # 只处理 audio/ 前缀的对象（与你的 EventBridge 规则保持一致，也做一次保护）
    if not key.startswith("audio/"):
        print(f"[INFO] Ignore non-audio object: s3://{bucket}/{key}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Ignored non-audio object"})
        }

    # 从 key 中解析 file_id 和扩展名
    # 例如 key = "audio/abcd-1234.mp3"
    filename = os.path.basename(key)         # "abcd-1234.mp3"
    if "." in filename:
        file_id, ext = filename.rsplit(".", 1)
    else:
        file_id, ext = filename, "mp3"
    ext = ext or "mp3"

    tmp_path = f"/tmp/{file_id}.{ext}"

    # ===== 从 S3 下载音频（走 AWS 内部网络，不用 presigned url）=====
    try:
        s3_client.download_file(bucket, key, tmp_path)
        print(f"[INFO] S3 download complete: s3://{bucket}/{key} -> {tmp_path}")
    except ClientError as e:
        print(f"[ERROR] S3 download failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"S3 download failed: {e}"}),
        }

    # ===== 音频分析 =====
    try:
        analyzer = get_analyzer()
        recording = Recording(analyzer, tmp_path, min_conf=MIN_CONFIDENCE)
        recording.analyze()
        detections = recording.detections
        print(f"[INFO] Audio analysis complete: {len(detections)} detections")
    except Exception as e:
        print(f"[ERROR] Audio analysis failed: {e}")
        detections = []

    # ===== 处理检测结果 =====
    tags = {}
    segments = []
    for d in detections:
        name = d.get('common_name', 'Unknown')
        conf = round(d.get('confidence', 0.0), 2)
        # 对于 tags，使用最高置信度
        tags[name] = max(tags.get(name, 0.0), conf)
        # 保存所有检测片段到 additional_metadata
        segments.append({
            "start_time": format_timestamp(d.get('start_time', 0.0)),
            "end_time":   format_timestamp(d.get('end_time', 0.0)),
            "species":    name,
            "confidence": conf
        })

    # ===== 构造对外可访问的 s3_url =====
    # 如果设置了 AUDIO_S3 环境变量就用它，否则用事件里的 bucket
    audio_bucket_for_url = AUDIO_BUCKET_ENV or bucket
    s3_url = f"https://{audio_bucket_for_url}.s3.amazonaws.com/{key}"

    # ===== 写入 / 更新 DynamoDB =====
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # 将 tags 转换为 DynamoDB Map 格式（confidence 值作为字符串）
    tags_map = {species: {"N": str(conf)} for species, conf in tags.items()}

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
            ":ft":   {"S": "Audio"},
            ":s":    {"S": s3_url},
            ":tg":   {"M": tags_map},
            ":u":    {"S": now_iso},
        }

        # 如果有检测片段，添加到 additional_metadata
        if segments:
            # 将 segments 转换为 DynamoDB 格式
            segments_list = []
            for seg in segments:
                segments_list.append({
                    "M": {
                        "start_time": {"S": seg["start_time"]},
                        "end_time":   {"S": seg["end_time"]},
                        "species":    {"S": seg["species"]},
                        "confidence": {"N": str(seg["confidence"])}
                    }
                })
            update_expression_parts.append("additional_metadata = :am")
            expression_attribute_values[":am"] = {
                "M": {
                    "segments": {"L": segments_list}
                }
            }

        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression="SET " + ", ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        print(
            f"[INFO] DynamoDB updated: file_id={file_id}, "
            f"file_type=Audio, s3_url={s3_url}, tags={tags}, segments={len(segments)}"
        )
    except ClientError as e:
        print(f"[ERROR] DynamoDB update failed: {e}")
        # 根据需要决定是否要抛出异常让 Lambda 失败重试
        raise

    # ===== 清理临时文件 =====
    try:
        os.remove(tmp_path)
    except OSError:
        pass

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"Processed audio {file_id}",
                "file_id": file_id,
                "bucket": bucket,
                "key": key,
                "tags": tags,
                "segments_count": len(segments),
            }
        ),
    }