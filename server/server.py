import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import time
import uuid
import json
import datetime
import logging
import urllib

class WSHandler(tornado.websocket.WebSocketHandler):

    SESSIONS = []

    def open(self, *args, **kwargs):
        logging.warning('Connection is open')
        if self not in self.SESSIONS:
            self.SESSIONS.append(self)
            logging.warning('Client Session added: {}'.format(self))

    def on_close(self):
        logging.warning('Connection is closed')
        if self in self.SESSIONS:
            self.SESSIONS.remove(self)
            logging.warning('Client Session removed: {}'.format(self))

    def on_message(self, message):
        logging.warning('Message recived: {}'.format(message))

    @classmethod
    def broadcast(cls,data):
        for session in cls.SESSIONS:
            logging.warning("--- Broadcast to {} ---".format(session))
            session.write_message(data)

    @classmethod
    def heartbeat(cls):
        logging.warning("--- Hearth Bit ---")
        logging.warning("--- SESSIONS: {}".format(cls.SESSIONS))
        return "ok"

    def check_origin(self, origin):
        logging.warning("--- Check Origin ---> {}".format(origin))
        parsed_origin = urllib.parse.urlparse(origin)
        return parsed_origin.netloc.endswith(".redhat.com")

class MainHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        self.render("index.html",title="Login NOS-PERF")
        # self.write({'status':'ok'})

    def post(self, *args, **kwargs):
        headers = {x: self.request.headers[x] for x in self.request.headers}
        payload = self.request.body
        data = {
            "id": str(uuid.uuid4()),
            "headers": headers,
            "timestamp": str(int(time.time() * 1000)),
            "payload": payload.decode('utf-8')
        }
        WSHandler.broadcast(data)
        self.write(json.dumps({
            'method': 'POST',
            'time': str(datetime.datetime.now().time()),
            'status': 'ok'
        }))


if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(
        tornado.web.Application(
            [
                (r'/ws',WSHandler),
                (r'/', MainHandler)
            ],
            websocket_ping_interval=10
        )
    )
    http_server.listen(8182)
    tornado.ioloop.PeriodicCallback(WSHandler.heartbeat, 30000).start()
    tornado.ioloop.IOLoop.instance().start()