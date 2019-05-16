FROM python:3.6-slim
WORKDIR /opt/app
EXPOSE 8182
ADD . .
RUN	pip install -r requirements.txt
CMD ["python","server.py"]
