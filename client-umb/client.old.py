
from tornado import escape
from tornado import gen
from tornado import httpclient
from tornado import httputil
from tornado import ioloop
from tornado import websocket

import functools
import json
import time
import os

APPLICATION_JSON = 'application/json'
DEFAULT_CONNECT_TIMEOUT = 60
DEFAULT_REQUEST_TIMEOUT = 60

class WebSocketClient():

    def __init__(self, * , connect_timeout=DEFAULT_CONNECT_TIMEOUT,request_timeout=DEFAULT_REQUEST_TIMEOUT):
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout

    def connect(self,url):
        headers = httputil.HTTPHeaders({'Content-Type': APPLICATION_JSON})
        request = httpclient.HTTPRequest(url=url,connect_timeout=self.connect_timeout,
                                         request_timeout=self.request_timeout,
                                         headers=headers)
        ws_conn = websocket.WebSocketClientConnection(
            ioloop.IOLoop.current(),
            request
        )
        ws_conn.connect_future.add_done_callback(self._connect_callback)


    def send(self,data):
        if not self._ws_connection:
            raise RuntimeError("WebSocket connection is closed")

        self._ws_connection.write_message(escape.utf8(json.dumps(data)))


    def close(self):
        if not self._ws_connection:
            raise RuntimeError("WebSocket connection is already closed")

        self._ws_connection.close()

    def _connect_callback(self,future):
        if future.exception() is None:
            self._ws_connection = future.result()
            self._on_connection_success()
            self._read_messages()
        else:
            self._on_connection_error(future.exception())

    @gen.coroutine
    def _read_messages(self):
        while True:
            msg = yield self._ws_connection.read_message()
            if msg is None:
                self._on_connection_close()
                break

            self._on_message(msg)

    def _on_message(self,msg):
        pass

    def _on_connection_success(self):
        pass

    def _on_connection_close(self):
        pass

    def _on_connection_error(self,exception):
        pass


class IndyPerfWSClient(WebSocketClient):

    def _on_message(self,msg):
        print(msg)
        # deadline = time.time() + 1
        # ioloop.IOLoop().instance().add_timeout(
        #     deadline,functools.partial(self.send,str(int(time.time())))
        # )

    def _on_connection_success(self):
        print('Connected!')
        self.send(str(int(time.time())))

    def _on_connection_close(self):
        print('Connection closed!')

    def _on_connection_error(self,exception):
        print('Connection error: %s' , exception)



def main():
    client = IndyPerfWSClient()
    # "wss://indyperf-ws-testa.7e14.starter-us-west-2.openshiftapps.com/ws"
    client.connect(
        os.getenv('INDYPERF_WS_SERVER', 'ws://localhost:8888/ws')
    )

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        client.close()





if __name__ == "__main__":
    main()