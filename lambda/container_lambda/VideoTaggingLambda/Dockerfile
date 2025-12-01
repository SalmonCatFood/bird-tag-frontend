FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
RUN yum install -y \
      gcc \
      gcc-c++ \
      libgcc \
      libstdc++ \
      mesa-libGL \
      ffmpeg \
    && yum clean all \
    && rm -rf /var/cache/yum

COPY requirements.txt /var/task/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /var/task/requirements.txt \
    && rm -rf /root/.cache/pip

# copy model
COPY video_tagging_lambda.py /var/task/image_tagging_lambda.py
COPY model.pt               /opt/model.pt

CMD ["video_tagging_lambda.handler"]