FROM public.ecr.aws/lambda/python:3.11

# System dependencies (including build tools for contourpy/matplotlib)
RUN yum install -y \
      gcc \
      gcc-c++ \
      make \
      python3-devel \
      meson \
      ninja-build \
      libgcc \
      libstdc++ \
      mesa-libGL \
      curl \
      tar \
      xz \
    && yum clean all \
    && rm -rf /var/cache/yum

# Ensure compilers are found by build systems
ENV CC=gcc
ENV CXX=g++

# Set config directories to /tmp for Lambda (read-only filesystem workaround)
ENV YOLO_CONFIG_DIR=/tmp/ultralytics
ENV MPLCONFIGDIR=/tmp/matplotlib

# Install ffmpeg (static build with libx264)
RUN curl -L -o /tmp/ffmpeg.tar.xz \
        https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && cp /tmp/ffmpeg-*-static/ffmpeg /usr/local/bin/ffmpeg \
    && cp /tmp/ffmpeg-*-static/ffprobe /usr/local/bin/ffprobe \
    && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
    && rm -rf /tmp/ffmpeg*
RUN ffmpeg -hide_banner -encoders | grep -i libx264

COPY requirements.txt /var/task/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /var/task/requirements.txt \
    && rm -rf /root/.cache/pip

# Lambda code（文件名与 handler 必须一致）
COPY video_tagging_lambda.py /var/task/video_tagging_lambda.py

# Model
COPY model.pt /opt/model.pt

CMD ["video_tagging_lambda.handler"]
