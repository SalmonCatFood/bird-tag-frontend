import os
import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta
import boto3
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.getenv('REGION', 'ap-southeast-2')
AUDIO_BUCKET = os.getenv('AUDIO_BUCKET')
DDB_TABLE = os.getenv('DDB_TABLE')

s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(DDB_TABLE)

analyzer = Analyzer()

def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def convert_floats(obj):

    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    return obj

def lambda_handler(event, context):
    try:

        rec = event['Records'][0]['s3']
        bucket = rec['bucket']['name']
        key = rec['object']['key']
        filename = os.path.basename(key)
        file_id = os.path.splitext(filename)[0]

        tmp_path = f"/tmp/{filename}"
        s3.download_file(bucket, key, tmp_path)

        resp = table.get_item(Key={'file_id': file_id})
        item = resp.get('Item', {})
        upload_ts = item.get('upload_timestamp', datetime.utcnow().isoformat() + 'Z')

        recording = Recording(analyzer, tmp_path, min_conf=0.3)
        recording.analyze()
        detections = recording.detections

        tags = {}
        segments = []
        for d in detections:
            name = d['common_name']
            conf = round(d.get('confidence', 0.0), 2)
            tags[name] = max(tags.get(name, 0), conf)
            segments.append({
                "start_time": format_timestamp(d.get('start_time', 0.0)),
                "end_time":   format_timestamp(d.get('end_time',   0.0)),
                "species":    name,
                "confidence": conf
            })


        updated_item = {
            "file_id":            file_id,
            "upload_timestamp":   upload_ts,
            "s3_url":             f"https://{AUDIO_BUCKET}.s3.amazonaws.com/{key}",
            "thumbnail_url":      "NULL",
            "file_type":          "audio",
            "status":             "DONE",
            "tags":               tags,
            "additional_metadata": {"segments": segments}
        }


        updated_item = convert_floats(updated_item)


        table.put_item(Item=updated_item)


        try:
            os.remove(tmp_path)
        except OSError:
            logger.warning(f"Unable to delete temp file {tmp_path}")

   
        return {
            "statusCode": 200,
            "body": json.dumps(updated_item, default=str)
        }

    except Exception as e:
        logger.error("failed to handle", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }