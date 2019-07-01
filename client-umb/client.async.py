
import asyncio
import websockets
import os
import json
import logging
import aiohttp
import ssl
import proton
from rhmsg.activemq.producer import AMQProducer

# json build-config payload & http endpoint
# {"kind":"BuildRequest","apiVersion":"build.openshift.io/v1","metadata":{"name":"indy-perf","creationTimestamp":None},"triggeredBy":[{"message":"Manually triggered"}],"dockerStrategyOptions":{},"sourceStrategyOptions":{}}
# 'https://paas.upshift.redhat.com:443/apis/build.openshift.io/v1/namespaces/nos-perf/buildconfigs/indy-perf/instantiate'

# http endpoint for github webhooks
# https://paas.upshift.redhat.com/oapi/v1/namespaces/nos-perf/buildconfigs/indy-perf/webhooks/fWXhF3kdYJQsbVZdvRqS/github
# ws://ws-server-nos-perf.7e14.starter-us-west-2.openshiftapps.com/ws

async def start():
    # Github Branch name from System Variable
    branch_name = os.getenv('GH_BRANCH','')
    # Default Service Account Token from System Variable
    default_token = os.getenv('DEFAULT_TOKEN','')
    if default_token != '':
        token = open(os.getenv('DEFAULT_TOKEN','')).read()
    else:
        token = ""
    # Certification file for SSL from System Variable
    cert = os.getenv('CERT_FILE','')
    # Provided URL for triggering build proccess or starting pipeline from System Variable
    build_url = os.getenv('URL_TRIGGER','')
    # WebSockets Endpoint URL provided from System Variable
    ws_endpoint = os.getenv('WS_SERVER', "")
    # List of Allowed Headers from Github webhooks POST request
    alowed = ["Accept", "User-Agent", "X-Github-Event", "X-Github-Delivery", "Content-Type", "X-Hub-Signature"]
    # Creating Default SSL Context
    sslcontext = ssl.create_default_context(cafile=cert)
    conn = aiohttp.TCPConnector(ssl_context=sslcontext)

    # UMB certificate files & endpoint
    topic = "VirtualTopic.eng.tightbeam."
    rh_cert = os.getenv("RH_CERT","")
    rh_key = os.getenv("RH_KEY","")
    rh_crt = os.getenv("RH_CRT","")
    amqp_url = os.getenv("AMQP_URL","")
    amqp_topic = os.getenv("AMQP_TOPIC","")


    #SSL connection present:
    print("--- SSL connection present: {}".format(proton.SSL.present()))
    print("--- RH Variables: rh_cert:{}  rh_key:{} rh_crt:{} amqp_url:{} amqp_topic:{}".format(rh_cert,rh_key,rh_crt,amqp_url,topic+amqp_topic))

    # Creating Client Session with provided SSL configuration
    async with aiohttp.ClientSession(connector=conn) as session:
        amqp_info_url = "https://messaging-devops-broker01.dev1.ext.devlab.redhat.com:8443/info"
        async with session.get(amqp_info_url) as resp:
            print(resp.status)
            print(await resp.text())


    # Opening WebSocket Connection to WebSocket server
    async with websockets.connect(ws_endpoint) as websocket:
        logging.warning('--- Opened Connection to Server ---')
        # sending websocket message to server
        await websocket.send(json.dumps({'msg':'TEST MESSAGE'}))
        while True:
            # Listening for recived messages from websocket server
            response = await websocket.recv()
            logRecivedMessage(response) # Log websocket recived message
            data = json.loads(response)
            payload = {}
            payload["payload"] = json.loads(data["payload"])
            logRecivedMessagePayload(payload["payload"]) # log websocket message payload from webhook
            # REF Github branch for building project
            ref = payload["payload"]["ref"].split("/")[2]
            """uncomment folowing lines if you wannt to start build proccess from openshift client API """
            # payload["metadata"] = {"name":"indy-perf"}
            # payload["triggeredBy"] = {}
            # Create Dictionary of allowed headers from rerouted webhook POST request
            headers = {x:y for x,y in data["headers"].items() if x in alowed}
            # Authorization header with token
            headers['Authorization'] = "Bearer {}".format(token)
            # Connection from websocket server is closed so terminate this iterations
            if response is None: break
            else:
                if branch_name != '' and ref in branch_name.split(","):
                    # If there is websocket message from server then send HTTP POST request
                    # to generated HTTP URL for triggering build proccess
                    # async with session.post(build_url, data=json.dumps(payload), headers=headers) as resp:
                    #     logResponseMessage(resp,build_url)
                    
                    amqp_props = dict()
                    amqp_props['subject'] = payload['payload']['head_commit']['message']
                    amqp_message = str(payload)  # "Test Message"
                    # send AMQP message to Red Hat UMB service
                    producer = AMQProducer(
                        urls=amqp_url,
                        certificate=rh_crt,
                        private_key=rh_key,
                        trusted_certificates=rh_cert,
                        topic=topic+amqp_topic
                    )
                    producer.send_msg(amqp_props,amqp_message.encode("utf-8"))
                else:
                    logDifferentBranchName(ref,branch_name)


def logRecivedMessage(msg):
    resp_txt = str(msg)
    rspn = json.loads(resp_txt.replace("\'", "\""))
    logging.warning("-- New Code Event ID: {}".format(rspn.get('id')))
    logging.warning("-- New Code Event Headers: {}".format(rspn.get("headers")))
    logging.warning("-- New Code Change {} Event".format(rspn.get("headers").get("X-Github-Event")))

def logRecivedMessagePayload(payload):
    logging.warning(payload.get('ref'))
    logging.warning(payload.get('pusher'))

async def logResponseMessage(resp,url):
    logging.warning('-- Sending HTTP POST to {}'.format(url))
    logging.warning(resp.status)
    logging.warning(resp.text())

def logGetResponseMessage(resp,url):
    logging.warning('-- Sending HTTP GET to {}'.format(url))
    logging.warning(resp.status)
    logging.warning(resp.text())

def logDifferentBranchName(ref,branch):
    logging.warning('This Repository branch name: {} is not equal to projects branch: {}'.format(ref, branch))

# Start Non-Blocking thread for Asynchronous Handling of Long Lived Connections
asyncio.get_event_loop().run_until_complete(start())
