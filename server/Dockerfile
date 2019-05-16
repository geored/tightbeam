FROM python:3.6-slim
WORKDIR /opt/app
ADD . .
RUN	pip install -r requirements.txt
EXPOSE 8182
CMD ["python","server.py"]
