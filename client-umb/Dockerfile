FROM centos/python-36-centos7
WORKDIR /opt/app
ENV RH_CERT "/opt/app/certs/ca-bundle.crt"
ENV RH_KEY "/opt/app/certs/msg-tightbeam.key.pem"
ENV RH_CRT "/opt/app/certs/msg-tightbeam.crt.pem"
ENV AMQP_URL "amqps://messaging-devops-broker01.dev1.ext.devlab.redhat.com:5671"
ENV AMQP_TOPIC "test"
USER root
ADD . .
RUN	pip install -r requirements.txt
RUN chgrp -R 0 /opt/app && \
    chmod -R g=u /opt/app
CMD ["python","client.async.py"]
