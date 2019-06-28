FROM python:3.6-slim
WORKDIR /opt/app
ENV DEFAULT_TOKEN "/var/run/secrets/kubernetes.io/serviceaccount/token"
ENV CERT_FILE "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
ADD . .
RUN apt-get update &&  apt-get install -y libevent-dev && apt-get install -y python3-dev && apt-get install -y libzbar-dev
RUN	pip install -r requirements.txt
CMD ["python","client.async.py"]
