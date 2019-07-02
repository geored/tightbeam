# -*- coding: utf-8 -*-

from proton import Message, SSLDomain
from proton.reactor import Container
from proton.handlers import MessagingHandler
import logging
import random


class TimeoutHandler(MessagingHandler):
    def __init__(self, url, conf, msgs, *args, **kws):
        super(TimeoutHandler, self).__init__(*args, **kws)
        self.url = url
        self.conf = conf
        self.msgs = msgs
        self.pending = {}
        self.log = logging.getLogger('rhmsg.activemq.producer.TimeoutHandler')

    def on_start(self, event):
        self.log.debug('Container starting')
        event.container.connected = False
        event.container.error_msgs = []
        if 'cert' in self.conf and 'key' in self.conf and 'cacert' in self.conf:
            ssl = SSLDomain(SSLDomain.MODE_CLIENT)
            ssl.set_credentials(self.conf['cert'], self.conf['key'], None)
            ssl.set_trusted_ca_db(self.conf['cacert'])
            ssl.set_peer_authentication(SSLDomain.VERIFY_PEER)
        else:
            ssl = None
        self.log.debug('connecting to %s', self.url)
        event.container.connect(url=self.url, reconnect=False, ssl_domain=ssl)
        connect_timeout = self.conf['connect_timeout']
        self.connect_task = event.container.schedule(connect_timeout, self)
        send_timeout = self.conf['send_timeout']
        self.timeout_task = event.container.schedule(send_timeout, self)

    def on_timer_task(self, event):
        if not event.container.connected:
            self.log.error('not connected, stopping container')
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None
            event.container.stop()
        else:
            # This should only run when called from the timeout task
            self.log.error('send timeout expired with %s messages unsent, stopping container',
                           len(self.msgs))
            event.container.stop()

    def on_connection_opened(self, event):
        event.container.connected = True
        self.connect_task.cancel()
        self.connect_task = None
        self.log.debug('connection to %s opened successfully', event.connection.hostname)
        self.send_msgs(event)

    def on_connection_closed(self, event):
        self.log.debug('disconnected from %s', event.connection.hostname)

    def send_msgs(self, event):
        sender = event.container.create_sender(event.connection, target=self.conf['address'])
        for msg in self.msgs:
            delivery = sender.send(msg)
            self.log.debug('sent msg: %s', msg.properties)
            self.pending[delivery] = msg
        sender.close()

    def update_pending(self, event):
        msg = self.pending[event.delivery]
        del self.pending[event.delivery]
        self.log.debug('removed message from self.pending: %s', msg.properties)
        if not self.pending:
            if self.msgs:
                self.log.error('%s messages unsent (rejected or released)', len(self.msgs))
            else:
                self.log.debug('all messages sent successfully')
            if self.timeout_task:
                self.log.debug('canceling timeout task')
                self.timeout_task.cancel()
                self.timeout_task = None
            self.log.debug('closing connection to %s', event.connection.hostname)
            event.connection.close()

    def on_settled(self, event):
        msg = self.pending[event.delivery]
        self.msgs.remove(msg)
        self.log.debug('removed message from self.msgs: %s', msg.properties)
        self.update_pending(event)

    def on_rejected(self, event):
        msg = self.pending[event.delivery]
        self.log.error('message was rejected: %s', msg.properties)
        self.update_pending(event)

    def on_released(self, event):
        msg = self.pending[event.delivery]
        self.log.error('message was released: %s', msg.properties)
        self.update_pending(event)

    def on_transport_tail_closed(self, event):
        if self.connect_task:
            self.log.debug('canceling connect timer')
            self.connect_task.cancel()
            self.connect_task = None
        if self.timeout_task:
            self.log.debug('canceling send timer')
            self.timeout_task.cancel()
            self.timeout_task = None

    def handle_error(self, objtype, event, level=logging.ERROR):
        endpoint = getattr(event, objtype, None)
        condition = getattr(endpoint, 'remote_condition', None) or \
            getattr(endpoint, 'condition', None)
        if condition:
            name = condition.name
            desc = condition.description
            self.log.log(level, '%s error: %s: %s', objtype, name, desc)
        else:
            name = '{0} error'.format(objtype)
            desc = 'unspecified'
            self.log.log(level, 'unspecified %s error', objtype)
        event.container.error_msgs.append((self.url, name, desc))

    def on_connection_error(self, event):
        self.handle_error('connection', event)

    def on_session_error(self, event):
        self.handle_error('session', event)

    def on_link_error(self, event):
        self.handle_error('link', event)
        self.log.error('closing connection to: %s', event.connection.hostname)
        event.connection.close()

    def on_transport_error(self, event):
        """
        Implement this handler with the same logic as the default handler in
        MessagingHandler, but log to our logger at INFO level, instead of the
        root logger with WARNING level.
        """
        self.handle_error('transport', event, level=logging.INFO)
        if event.transport and event.transport.condition and \
           event.transport.condition.name in self.fatal_conditions:
            self.log.error('closing connection to: %s', event.connection.hostname)
            event.connection.close()


class AMQProducer(object):

    def __init__(self, host=None, port=None,
                 urls=None,
                 certificate=None, private_key=None,
                 trusted_certificates=None,
                 queue=None, topic=None,
                 timeout=None):
        if isinstance(urls, (list, tuple)):
            pass
        elif urls:
            urls = [urls]
        elif host:
            urls = ['amqps://{0}:{1}'.format(host, port or 5671)]
        else:
            raise RuntimeError('either host or urls must be specified')
        self.urls = urls
        self.conf = {
            'cert': certificate,
            'key': private_key,
            'cacert': trusted_certificates,
            'connect_timeout': timeout or 60,
            'send_timeout': timeout or 60
        }
        if queue:
            self.through_queue(queue)
        elif topic:
            self.through_topic(topic)
        else:
            self.address = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def through_queue(self, address):
        self.address = self.build_address('queue', address)

    def through_topic(self, address):
        self.address = self.build_address('topic', address)

    def build_address(self, channel, address):
        return '{0}://{1}'.format(channel, address)

    def _send_all(self, messages):
        messages = list(messages)
        errors = []
        for url in sorted(self.urls, key=lambda k: random.random()):
            container = Container(TimeoutHandler(url, self.conf, messages))
            container.run()
            errors.extend(container.error_msgs)
            if not messages:
                break
        else:
            error_strs = ['{0}: {1}: {2}'.format(*e) for e in errors]
            raise RuntimeError('could not send {0} message{1} to any destinations, '
                               'errors:\n{2}'.format(len(messages),
                                                     len(messages) != 1 and 's' or '',
                                                     '\n'.join(error_strs)))

    def send(self, *messages):
        """
        Send a list of messages.

        Each argument is a proton.Message.
        """
        assert self.address, \
            'Must call through_queue or through_topic in advance.'

        self.conf['address'] = self.address
        self._send_all(messages)

    def _build_msg(self, props, body, attrs=None):
        """
        Build and return a proton.Message.

        Arguments:
        props (dict): Message properties
        body (object): Message body
        attrs (dict): Attributes to set on the message.
        """
        msg = Message(properties=props, body=body)
        if attrs:
            for name, value in attrs.items():
                setattr(msg, name, value)
        return msg

    def send_msg(self, props, body, **kws):
        """
        Send a single message.

        Arguments:
        props (dict): Message properties
        body (str): Message body. Should be utf-8 encoded text.

        Any keyword arguments will be treated as attributes to set on the
        underlying Message.
        """
        msg = self._build_msg(props, body, kws)
        self.send(msg)

    def send_msgs(self, messages):
        """
        Send a list of messages.

        Arguments:
        messages (list): A list of 2-element lists/tuples.
          tuple[0]: A dict of message headers.
          tuple[1]: Message body. Should be utf-8 encoded text.

        If the tuple has a third element, it is treated as a dict containing
        attributes to be set on the underlying Message.
        """
        msgs = []
        for message in messages:
            msgs.append(self._build_msg(*message))
        self.send(*msgs)
