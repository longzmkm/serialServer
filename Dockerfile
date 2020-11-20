FROM python:3.7-alpine

ADD ./requirements.txt /code/requirements.txt
WORKDIR /code

RUN pip install --no-cache-dir -r  requirements.txt

ADD . .
RUN pwd
CMD ["python","./code/manage.py"]