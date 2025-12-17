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

def get_detect_counts(image_path: str, confidence: float = 0.5, save_annotated: bool = False, output_path: str = None) -> dict:
    """
    使用 YOLO 对图片进行推理，返回 {class_name: count} 的统计字典
    
    Args:
        image_path: 输入图片路径
        confidence: 置信度阈值
        save_annotated: 是否保存标注后的图片
        output_path: 输出图片路径，如果为None且save_annotated为True，则保存到原图同目录，文件名添加_annotated后缀
    
    Returns:
        {class_name: count} 的统计字典
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

    # 如果检测到目标且需要保存标注图片
    if save_annotated and detections.class_id is not None and len(detections) > 0:
        # 创建标注器
        box_annotator = sv.BoxAnnotator(thickness=2)
        label_annotator = sv.LabelAnnotator(text_thickness=1, text_scale=0.5)
        
        # 生成标签（类别名称 + 置信度）
        labels = [
            f"{class_dict[int(cls_id)]} {conf:.2f}"
            for cls_id, conf in zip(detections.class_id, detections.confidence)
        ]
        
        # 绘制边界框和标签
        annotated_img = box_annotator.annotate(scene=img.copy(), detections=detections)
        annotated_img = label_annotator.annotate(scene=annotated_img, detections=detections, labels=labels)
        
        # 确定输出路径
        if output_path is None:
            # 在原图路径基础上添加 _annotated 后缀
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_annotated{ext}"
        
        # 保存标注后的图片
        cv.imwrite(output_path, annotated_img)
        print(f"[INFO] Annotated image saved to: {output_path}")

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
    annotated_image_path = None
    try:
        # 生成标注后的图片保存路径
        annotated_image_path = f"/tmp/{file_id}_annotated.{ext}"
        counts = get_detect_counts(tmp_path, confidence=0.5, save_annotated=True, output_path=annotated_image_path)
        print(f"[INFO] model run complete: {counts}")
    except Exception as e:
        print(f"[ERROR] model run failed: {e}")
        counts = {}

    # ===== 上传标注后的图片到 S3 =====
    annotated_s3_key = None
    annotated_image_s3_url = None
    if annotated_image_path and os.path.exists(annotated_image_path):
        images_bucket = IMAGES_BUCKET_ENV or bucket
        annotated_s3_key = f"tagging_output/{file_id}_annotated.{ext}"
        try:
            # 根据文件扩展名确定 ContentType
            content_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            content_type = content_type_map.get(ext.lower(), 'image/jpeg')
            
            s3_client.upload_file(
                annotated_image_path,
                images_bucket,
                annotated_s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ContentDisposition': 'inline'  # 确保在浏览器中显示而不是下载
                }
            )
            print(f"[INFO] Annotated image uploaded: s3://{images_bucket}/{annotated_s3_key} with ContentType: {content_type}")
            
            # 生成 annotated image URL
            images_bucket_for_url = IMAGES_BUCKET_ENV or bucket
            annotated_image_s3_url = f"https://{images_bucket_for_url}.s3.amazonaws.com/{annotated_s3_key}"
            print(f"[INFO] Annotated image URL: {annotated_image_s3_url}")
        except ClientError as e:
            print(f"[ERROR] Failed to upload annotated image: {e}")
            # 上传失败不影响主流程，只记录错误

    # ===== 构造对外可访问的 s3_url =====
    # 如果设置了 IMAGES_S3 环境变量就用它，否则用事件里的 bucket
    images_bucket_for_url = IMAGES_BUCKET_ENV or bucket
    s3_url = f"https://{images_bucket_for_url}.s3.amazonaws.com/{key}"

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
            ":ft":   {"S": "Image"},
            ":s":    {"S": s3_url},
            ":tg":   {"M": tags_map},
            ":u":    {"S": now_iso},
        }
        
        if annotated_image_s3_url:
            update_expression_parts.append("annotated_output_url = :ao")
            expression_attribute_values[":ao"] = {"S": annotated_image_s3_url}
        
        ddb_client.update_item(
            TableName=METADATA_TABLE,
            Key={"file_id": {"S": file_id}},
            UpdateExpression="SET " + ", ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )
        print(
            f"[INFO] DynamoDB updated: file_id={file_id}, "
            f"file_type=Image, s3_url={s3_url}, tags={counts}, "
            f"annotated_output_url={annotated_image_s3_url}"
        )
    except ClientError as e:
        print(f"[ERROR] DynamoDB update failed: {e}")
        # 根据需要决定是否要抛出异常让 Lambda 失败重试
        raise

    # ===== 清理临时文件 =====
    for temp_file in [tmp_path, annotated_image_path]:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
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
