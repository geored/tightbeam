
import asyncio
import websockets
import os
import json
import logging
import aiohttp
import ssl

# json build-config payload & http endpoint
# {"kind":"BuildRequest","apiVersion":"build.openshift.io/v1","metadata":{"name":"indy-perf","creationTimestamp":None},"triggeredBy":[{"message":"Manually triggered"}],"dockerStrategyOptions":{},"sourceStrategyOptions":{}}
# 'https://paas.upshift.redhat.com:443/apis/build.openshift.io/v1/namespaces/nos-perf/buildconfigs/indy-perf/instantiate'

# http endpoint for github webhooks
# https://paas.upshift.redhat.com/oapi/v1/namespaces/nos-perf/buildconfigs/indy-perf/webhooks/fWXhF3kdYJQsbVZdvRqS/github
# ws://ws-server-nos-perf.7e14.starter-us-west-2.openshiftapps.com/ws

async def start():
    # Github Branch name
    branch_name = os.getenv('GH_BRANCH','')
    # Default Service Account Token
    token = open(os.getenv('DEFAULT_TOKEN','')).read()
    # Certification file for SSL
    cert = os.getenv('CERT_FILE','')
    # Provided URL for triggering build proccess or starting pipeline
    build_url = os.getenv('URL_TRIGGER','')
    # WebSockets Endpoint URL provided
    ws_endpoint = os.getenv('WS_SERVER', "")
    # List of Allowed Headers from Github webhooks POST request
    alowed = ["Accept", "User-Agent", "X-Github-Event", "X-Github-Delivery", "Content-Type", "X-Hub-Signature"]
    # Creating Default SSL Context
    sslcontext = ssl.create_default_context(cafile=cert)
    conn = aiohttp.TCPConnector(ssl_context=sslcontext)

    # Opening WebSocket Connection to WebSocket server
    async with websockets.connect(ws_endpoint) as websocket:
        logging.warning('--- Opened Connection to Server ---')
        # sending websocket message to server
        await websocket.send(json.dumps({'msg':'TEST MESSAGE'}))
        # Creating Client Session with provided SSL configuration
        async with aiohttp.ClientSession(connector=conn) as session:

            while True:
                # Listening for recived messages from websocket server
                response = await websocket.recv()
                logRecivedMessage(response)
                data = json.loads(response)
                payload = {}
                payload["payload"] = json.loads(data["payload"])
                logRecivedMessagePayload(payload["payload"])
                # REF Github branch for building project
                ref = payload["payload"]["ref"].split("/")[2]
                """uncomment folowing lines if you wannt to start build proccess from openshift client API """
                # payload["metadata"] = {"name":"indy-perf"}
                # payload["triggeredBy"] = {}

                headers = {x:y for x,y in data["headers"].items() if x in alowed}
                # Authorization header with token
                headers['Authorization'] = "Bearer {}".format(token)
                # Connection from websocket server is closed so terminate this iterations
                if response is None: break
                else:
                    if branch_name != '' and branch_name == ref:
                        # If there is websocket message from server then send HTTP POST request
                        # to generated HTTP URL for triggering build proccess
                        async with session.post(build_url, data=json.dumps(payload), headers=headers) as resp:
                            logging.warning(resp.status)
                            logging.warning(await resp.text())
                    else:
                        logging.warning('This Repository branch name: {} is not equal to projects branch: {}'.format(ref,branch_name))


def logRecivedMessage(msg):
    resp_txt = str(msg)
    rspn = json.loads(resp_txt.replace("\'", "\""))
    logging.warning("-- New Code Event ID: {}".format(rspn.get('id')))
    logging.warning("-- New Code Event Headers: {}".format(rspn.get("headers")))
    logging.warning("-- New Code Change {} Event".format(rspn.get("headers").get("X-Github-Event")))

def logRecivedMessagePayload(payload):
    logging.warning(payload.get('ref'))
    logging.warning(payload.get('pusher'))


# Start Non-Blocking thread for Asynchronous Handling of Long Lived Connections
asyncio.get_event_loop().run_until_complete(start())