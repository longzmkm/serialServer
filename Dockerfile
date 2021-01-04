FROM python:3.7-alpine
ENV userid=user_id container=container_id
ADD ./requirements.txt /code/requirements.txt
WORKDIR /code

RUN pip install --no-cache-dir -r  requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

ADD . .
CMD ["python","./code/manage.py"]