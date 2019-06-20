FROM python:3
WORKDIR /opt/app
ADD . .
RUN pip install -r requirements.txt && \
    cd tightbeam-rhmsg && python setup.py install
EXPOSE 8080
CMD ["python" , "amqp-tightbeam.py"]
