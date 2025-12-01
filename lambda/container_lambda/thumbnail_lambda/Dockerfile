FROM public.ecr.aws/lambda/python:3.9

COPY requirements.txt ./

RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt --target /var/task


COPY lambda_handler.py ./

CMD ["lambda_handler.handler"]
