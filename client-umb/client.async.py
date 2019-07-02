
import asyncio
import websockets
import os
import json
import logging
import aiohttp
import ssl
import proton
from rhmsg.activemq.producer import AMQProducer

async def start():
    # Github Branch name from System Variable
    branch_name = os.getenv('GH_BRANCH','')
    # Provided URL for triggering build proccess or starting pipeline from System Variable
    build_url = os.getenv('URL_TRIGGER','')
    # WebSockets Endpoint URL provided from System Variable
    ws_endpoint = os.getenv('WS_SERVER', "")
    # List of Allowed Headers from Github webhooks POST request
    alowed = ["Accept", "User-Agent", "X-Github-Event", "X-Github-Delivery", "Content-Type", "X-Hub-Signature"]
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
            # Create Dictionary of allowed headers from rerouted webhook POST request
            payload['headers'] =  {x:y for x,y in data["headers"].items() if x in alowed}
            # Connection from websocket server is closed so terminate this iterations
            if response is None: break
            else:
                if branch_name != '' and ref in branch_name.split(","):
                    amqp_props = dict()
                    amqp_props['subject'] = payload['payload']['head_commit']['message']
                    amqp_message = str(payload)  # "Test Message"
                    producer = AMQProducer(
                        urls=amqp_url,
                        certificate=rh_crt,
                        private_key=rh_key,
                        trusted_certificates=rh_cert,
                        topic=topic+amqp_topic
                    )
                    # send AMQP message to Red Hat UMB service
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
