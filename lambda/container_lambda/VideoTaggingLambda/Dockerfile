FROM public.ecr.aws/lambda/python:3.11

# 1. 系统依赖
RUN yum install -y \
      libgcc \
      libstdc++ \
      mesa-libGL \
      ffmpeg \
    && yum clean all \
    && rm -rf /var/cache/yum

# 2. Python 依赖
COPY requirements.txt /var/task/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /var/task/requirements.txt \
    && rm -rf /root/.cache/pip

# 3. 代码 + 模型
COPY video_tagging_lambda.py /var/task/video_tagging_lambda.py
COPY model.pt               /opt/model.pt

# 4. 环境变量
ENV AWS_REGION=us-east-1
ENV VIDEO_BUCKET=zaii0001-a4-video
ENV THUMB_BUCKET=zaii0001-a4-thumbnails
ENV DDB_TABLE=zaii0001-A4-Metadata
ENV MODEL_PATH=/opt/model.pt

# 5. Handler
CMD ["video_tagging_lambda.handler"]