# Stage 1: build static FFmpeg (base on Alpine 3.12)
FROM alpine:3.12 AS ffmpeg-builder

RUN apk add --no-cache wget xz tar

# download git to build FFmpeg
RUN wget -qO /tmp/ffmpeg.tar.xz \
      https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz \
 && mkdir -p /tmp/ffmpeg-build \
 && tar xJf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg-build \
 && mv /tmp/ffmpeg-build/ffmpeg-git-*-amd64-static/ffmpeg /usr/local/bin/ \
 && mv /tmp/ffmpeg-build/ffmpeg-git-*-amd64-static/ffprobe /usr/local/bin/

# Stage 2: build AWS Lambda Python 3.11 image
FROM public.ecr.aws/lambda/python:3.11

WORKDIR /var/task

# 1. install python to lambda work dir
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# 2.dependencies: libsndfile (for .wav) and tar
RUN yum clean all \
 && yum makecache \
 && yum install -y libsndfile.x86_64 tar \
 && yum clean all

# 3. from ffmpeg-builder copy FFmpeg binary
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/
COPY --from=ffmpeg-builder /usr/local/bin/ffprobe /usr/local/bin/

# 4. Set Numba cache
ENV NUMBA_CACHE_DIR=/tmp/numba_cache
RUN mkdir -p /tmp/numba_cache


COPY lambda_handler.py ${LAMBDA_TASK_ROOT}

ENV REGION="us-east-1" \
    AUDIO_BUCKET="zaii0001-a4-audio" \
    DDB_TABLE="zaii0001-A4-Metadata"

CMD ["lambda_handler.lambda_handler"]
