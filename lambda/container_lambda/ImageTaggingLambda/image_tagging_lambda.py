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
IMAGES_BUCKET_ENV = os.getenv("IMAGES_S3")      # 可选：如果你希望 s3_url 固定用某个 bucket
METADATA_TABLE = os.getenv("METADATA_TABLE")
MODEL_PATH     = os.getenv("MODEL_PATH", "/opt/model.pt")

s3_client  = boto3.client("s3",  region_name=REGION)
ddb_client = boto3.client("dynamodb", region_name=REGION)

# ===== YOLO 模型懒加载 =====
_model = None
def get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model

def get_detect_counts(image_path: str, confidence: float = 0.5) -> dict:
    """
    使用 YOLO 对图片进行推理，返回 {class_name: count} 的统计字典
    """
    model = get_model()
    class_dict = model.names  # id -> class name

    img = cv.imread(image_path)
    if img is None:
        raise RuntimeError(f"cannot read image: {image_path}")

    result = model(img)[0]
    detections = sv.Detections.from_ultralytics(result)
    if detections.class_id is not None:
        mask = detections.confidence > confidence
        detections = detections[mask]
    else:
        detections = sv.Detections.empty()

    counts = {}
    if detections.class_id is not None:
        for cls_id in detections.class_id.tolist():
            species = class_dict[int(cls_id)]
            counts[species] = counts.get(species, 0) + 1

    return counts

# ===== 主 handler =====
def handler(event, context):
    """
    期望事件来源：
    - EventBridge 规则：source = "aws.s3", detail-type = "Object Created"
    - event["detail"]["bucket"]["name"] 为 bucket
    - event["detail"]["object"]["key"] 为对象 key，例如 "image/xxx.jpg"
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

    # 只处理 image/ 前缀的对象（与你的 EventBridge 规则保持一致，也做一次保护）
    if not key.startswith("image/"):
        print(f"[INFO] Ignore non-image object: s3://{bucket}/{key}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Ignored non-image object"})
        }

    # 从 key 中解析 file_id 和扩展名
    # 例如 key = "image/abcd-1234.jpg"
    filename = os.path.basename(key)         # "abcd-1234.jpg"
    if "." in filename:
        file_id, ext = filename.rsplit(".", 1)
    else:
        file_id, ext = filename, "jpg"
    ext = ext or "jpg"

    tmp_path = f"/tmp/{file_id}.{ext}"

    # ===== 从 S3 下载图片（走 AWS 内部网络，不用 presigned url）=====
    try:
        s3_client.download_file(bucket, key, tmp_path)
        print(f"[INFO] S3 download complete: s3://{bucket}/{key} -> {tmp_path}")
    except ClientError as e:
        print(f"[ERROR] S3 download failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"S3 download failed: {e}"}),
        }

    # ===== 模型推理 =====
    try:
        counts = get_detect_counts(tmp_path, confidence=0.5)
        print(f"[INFO] model run complete: {counts}")
    except Exception as e:
        print(f"[ERROR] model run failed: {e}")
        counts = {}

    # ===== 构造对外可访问的 s3_url =====
    # 如果设置了 IMAGES_S3 环境变量就用它，否则用事件里的 bucket
    images_bucket_for_url = IMAGES_BUCKET_ENV or bucket
    s3_url = f"https://{images_bucket_for_url}.s3.amazonaws.com/{key}"

    # ===== 写入 / 更新 DynamoDB =====
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tags_map = {species: {"N": str(cnt)} for species, cnt in counts.items()}

    try:
        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression=(
                "SET #S = :done, "
                "file_type = :ft, "
                "s3_url = :s, "
                "tags = :tg, "
                "upload_timestamp = :u"
            ),
            ExpressionAttributeNames={"#S": "status"},
            ExpressionAttributeValues={
                ":done": {"S": "DONE"},
                ":ft":   {"S": "Image"},
                ":s":    {"S": s3_url},
                ":tg":   {"M": tags_map},
                ":u":    {"S": now_iso},
            },
        )
        print(
            f"[INFO] DynamoDB updated: file_id={file_id}, "
            f"file_type=Image, s3_url={s3_url}, tags={counts}"
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
                "message": f"Processed image {file_id}",
                "file_id": file_id,
                "bucket": bucket,
                "key": key,
                "tags": counts,
            }
        ),
    }
