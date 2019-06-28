# -*- coding: utf-8 -*-

from proton.handlers import MessagingHandler
from proton import SSLDomain
from proton.reactor import Container
from proton.reactor import DurableSubscription
from proton.reactor import Selector

import logging
logger = logging.getLogger('activemq.Consumer')


class ReceiverHandler(MessagingHandler):
    """Handler to deal with received messages"""

    def __init__(self, urls, address, callback,
                 data=None, ssl_domain=None, selector=None,
                 subscription_name=None,
                 **super_handler_kwargs):
        """Initialize handler

        :param list urls: list of URLs of brokers. Each of URL could in
            format ``hostname[:port]``.
        :param str address: address from which to receive messages.
        :param callable callback: user-defined method to be called when a
            message is received.
        :param data: user data that will be passed to ``callback`` method. It
            is optional.
        :param ssl_domain: object containing SSL certificate and private key.
            It is optional. If omitted, do not connect to broker over SSL.
        :type ssl_domain: ``proton.SSLDomain``.
        :param str selector: filter string used to select messages that meet
            specific criteria. For a detailed syntax infomration of a usable
            selector, please refer to
            https://activemq.apache.org/selectors.html. It is optional. If
            omitted, every message sent to ``address`` will arrive at and be
            passed to ``callback``.
        :param str subscription_name: name to use to identify the durable
            subscription. It will also be used as the client ID. If it is
            None, the subscription will be non-durable, and the client ID
            will be random.
        :param dict super_handler_kwargs: parameters that super class
            ``MessagingHandler`` accepts. If manual control of accepting a
            mesaging is required, set ``auto_accept`` to False.
        """
        super(ReceiverHandler, self).__init__(**super_handler_kwargs)

        self.auto_accept = super_handler_kwargs.get('auto_accept', True)
        self.urls = urls
        if selector is None:
            self.selector = None
        else:
            self.selector = Selector(selector)
        self.ssl_domain = ssl_domain
        self.callback = callback
        self.data = data
        self.address = address
        self.subscription_name = subscription_name
        self.result = None

    def on_start(self, event):
        # See:
        # http://qpid.2158936.n2.nabble.com/
        # Connecting-to-durable-consumer-Qpid-Proton-Python-td7659185.html
        # for an explanation of the steps required to create and retain a durable
        # subscription.
        recv_opts = self.selector and [self.selector] or []
        if self.subscription_name:
            event.container.container_id = self.subscription_name
            recv_opts.append(DurableSubscription())
        conn = event.container.connect(urls=self.urls,
                                       ssl_domain=self.ssl_domain,
                                       heartbeat=500)
        event.container.create_receiver(conn, self.address,
                                        name=self.subscription_name,
                                        options=recv_opts)

    def on_message(self, event):
        """Call callback to deal with received message

        callback method uses return value to control whether to continue
        receiving next messages, or whether to accept (aka ack) received
        message that is just handled when automatic accept is disabled.

        - When ``None`` is returned, it means to continue receiving messages.

        - When ``True`` or a non-boolean value is returned, it tells message
          has been handled and to stop receiving other incoming messages.

        - When automatic accept is disable, callback method should return a
          tuple of two elements ``(return value, whether to accept handled
          message)``.

        :param event: event containing the message to be handled.
        :type event: ``proton.Event``.
        """
        handle_result = self.callback(event.message, self.data)
        self.on_message_handled(event, handle_result)

    def close_conn(self, event):
        """Called when we're done processing messages.

        If subscription_name is not None, we've created a durable subscription.
        We may want to process more messages from it in the future, so call
        receiver.detach(), which leaves the subscription intact on the broker.
        If subscription_name is None, call receiver.close(), explicitly
        removing the subscription from the broker.

        :param event: event object passed to handlers.
        :type event: ``proton.Event``.
        """
        if self.subscription_name:
            event.receiver.detach()
        else:
            event.receiver.close()
        event.connection.close()

    def on_message_handled(self, event, callback_result):
        """Called after received message is handled by callback

        :param event: event object when call and passed in ``on_message``.
        :type event: ``proton.Event``.
        :param callback_result: return value from callback method.
        """
        self._manual_accept_if_enabled(event, callback_result)

        # Check if stop receiving next messages according to return value from
        # callback.
        if self.result is not None:
            if isinstance(self.result, bool):
                if self.result:
                    self.close_conn(event)
            else:
                self.close_conn(event)

    def _manual_accept_if_enabled(self, event, callback_result):
        """Manual accept message if enable otherwise it is auto_accept

        :param event: refer to ``on_message_handled``.
        :type event: ``proton.Event``.
        :param callback_result: refer to ``on_message_handled``.
        :raises ValueError: if manual accept is enabled but callback method
            does not return a tuple containing the second value to tell
            whether to accept message.
        """
        if self.auto_accept:
            self.result = callback_result
        else:
            try:
                self.result, accepted = callback_result
            except (TypeError, ValueError):
                # TypeError can happen if the callback returns None.
                # ValueError will happen if the callback returns an iterable
                # result with len() != 2.
                raise ValueError('Manual ack is enabled, but callback method '
                                 'does not tell if message is accepted.')
            if accepted:
                self.accept(event.delivery)
            else:
                self.release(event.delivery, delivered=True)


class AMQConsumer(object):

    def __init__(self, urls, certificate=None, private_key=None,
                 trusted_certificates=None):
        self.urls = urls
        self.ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
        self.ssl_domain.set_credentials(certificate, private_key, None)
        self.ssl_domain.set_trusted_ca_db(trusted_certificates)
        self.ssl_domain.set_peer_authentication(SSLDomain.VERIFY_PEER)

    def consume(self, address, callback,
                data=None, selector=None, auto_accept=True,
                subscription_name=None):
        """Start to consume messages

        :param str address: refer to ``ReceiverHandler.__init__``.
        :param callable callback: refer to ``ReceiverHandler.__init__``.
        :param data: refer to ``ReceiverHandler.__init__``.
        :param str selector: refer to ``ReceiverHandler.__init__``.
        :param bool auto_accept: whether to accept message automatically.
            Defaults to ``True``, that is to use default behaivor of
            ``proton.MessagingHandler``. Otherwise, received message will be
            accepted according to return value from ``callback``. For
            detailed information, refer to ``ReceiverHandler.on_message``.
        :param str subscription_name: name to use to identify the durable
            subscription. It will also be used as the client ID. If it is
            None, the subscription will be non-durable, and the client ID
            will be random.
        :return: the return value of ``callback`` once a message is handled.
            Or, the value returned when the last time ``callback`` is called.
        """
        handler = ReceiverHandler(self.urls, address,
                                  callback, data=data,
                                  selector=selector,
                                  ssl_domain=self.ssl_domain,
                                  auto_accept=auto_accept,
                                  subscription_name=subscription_name)
        Container(handler).run()
        return handler.result
