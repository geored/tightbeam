FROM python:3.6-slim
WORKDIR /opt/app
ENV DEFAULT_TOKEN "/var/run/secrets/kubernetes.io/serviceaccount/token"
ENV CERT_FILE "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
ADD . .
RUN	pip install -r requirements.txt
CMD ["python","client.async.py"]
