
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time
import json
import os


def on_message(ws,message):
    print('=> Got Message {}'.format(message))

def on_error(ws,error):
    print('=> ERROR {}'.format(error))

def on_close(ws):
    print('===> CONNECTION CLOSED <===')

def on_open(ws):
    def run(*args):
        for i in range(10):
            time.sleep(5)
            ws.send(json.dumps({'message':'Everything ok?'}))
        time.sleep(1)
        ws.close()
        print('===>  Thread Terminating...')
    thread.start_new_thread(run,())

if __name__ == "__main__":
    websocket.enableTrace(True)
    # "wss://indyperf-ws-server-3-testa.7e14.starter-us-west-2.openshiftapps.com/ws",
    # "ws://localhost:8888/ws",
    # os.getenv('WS_SERVER','ws://localhost:8888')
    # https://ws-test-1-testa.7e14.starter-us-west-2.openshiftapps.com
    ws = websocket.WebSocketApp(
        "wss://ws-test-1-testa.7e14.starter-us-west-2.openshiftapps.com/ws",
        on_message = on_message ,
        on_error = on_error ,
        on_close = on_close
    )
    ws.on_open = on_open
    ws.run_forever()


