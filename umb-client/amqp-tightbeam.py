import tornado.httpserver
import tornado.ioloop
import tornado.web
import sys
import os
import json
import time

class MainHandler(tornado.web.RequestHandler):

    def get(self,*args,**kwargs):
        # self.render("index.html",title="Main Server for Sending AMQP Event Messages")
        self.write( json.dumps( {"service":"ok","time":time.time()} ) )

    def post(self,*args,**kwargs):
        payload = self.request.body
        data = payload.decode('utf-8')
        json_data = json.loads(data)
        amqp_producer = "/usr/local/bin/amq-producer"
        ca_cert_file = " --ca-certs=./certs/RH-IT-Root-CA.crt"
        cert_key = " --certificate-file=./certs/msg-tightbeam.crt.pem"
        cert_pem = " --private-key-file=./certs/msg-tightbeam.key.pem"
        topic = " --topic=VirtualTopic.eng.tightbeam.{}".format( json_data['tb_topic'] if json_data['tb_topic'] else 'test')
        subject = " --subject={}".format(json_data['subject'] if json_data['subject'] else 'Testing AMQP')
        send_event = amqp_producer+ca_cert_file+cert_key+cert_pem+topic+subject+" "+json.dumps(json_data)
        os.system(send_event)
        self.write(json.dumps({"command":"executed","time":time.time(),"payload":json_data}))


if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(
      tornado.web.Application([(r'/', MainHandler)])
    )
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
