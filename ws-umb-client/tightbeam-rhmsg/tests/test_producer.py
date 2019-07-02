# tests for the AMQProducer class

import six

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import Mock, patch, DEFAULT
from rhmsg.activemq.producer import AMQProducer, TimeoutHandler
if not hasattr(unittest.TestCase, 'assertRaisesRegex') and \
   hasattr(unittest.TestCase, 'assertRaisesRegexp'):
    # assertRaisesRegexp was renamed to assertRaisesRegex in unittest 3.2.
    # Make 3.1 forward-compatible.
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

PRODUCER_CONFIG = {'urls': ['amqps://amq1.example.com:5671', 'amqps://amq2.example.com:5671'],
                   'certificate': 'cert', 'private_key': 'key',
                   'trusted_certificates': 'trusted_certs'}

HANDLER_CONFIG = {'cert': 'cert', 'key': 'key', 'cacert': 'cacert',
                  'connect_timeout': 10, 'send_timeout': 60,
                  'address': 'topic://test-topic'}


class TestProducer(unittest.TestCase):

    def setUp(self):
        self.producer = AMQProducer(**PRODUCER_CONFIG)

    def test_queue(self):
        self.producer.through_queue('test-queue')
        self.assertEqual(self.producer.address,
                         'queue://test-queue')

    def test_topic(self):
        self.producer.through_topic('test-topic')
        self.assertEqual(self.producer.address,
                         'topic://test-topic')

    def test_send_noaddr(self):
        with self.assertRaises(AssertionError):
            self.producer.send(Mock())

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    def test_send_queue(self, Container, TimeoutHandler):
        self.producer.through_queue('test-queue')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        msg = Mock()
        with self.producer as prod:
            prod.send(msg)
        self.assertEquals(self.producer.address, self.producer.conf['address'])
        Container.return_value.run.assert_called_once_with()

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    def test_send_topic(self, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        msg = Mock()
        with self.producer as prod:
            prod.send(msg)
        self.assertEquals(self.producer.address, self.producer.conf['address'])
        Container.return_value.run.assert_called_once_with()

    def test_certs(self):
        self.assertEquals(self.producer.conf['cert'], PRODUCER_CONFIG['certificate'])
        self.assertEquals(self.producer.conf['key'], PRODUCER_CONFIG['private_key'])
        self.assertEquals(self.producer.conf['cacert'], PRODUCER_CONFIG['trusted_certificates'])

    def test_attrs(self):
        self.assertIsNotNone(self.producer.urls)
        self.assertIsNotNone(self.producer.conf)
        self.assertIsNone(self.producer.address)

    @patch.dict(PRODUCER_CONFIG, queue='test-queue')
    def test_init_queue(self):
        prod = AMQProducer(**PRODUCER_CONFIG)
        self.assertIsNotNone(prod.address)
        self.assertIn('queue://', prod.address)

    @patch.dict(PRODUCER_CONFIG, topic='test-topic')
    def test_init_topic(self):
        prod = AMQProducer(**PRODUCER_CONFIG)
        self.assertIsNotNone(prod.address)
        self.assertIn('topic://', prod.address)

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    @patch('rhmsg.activemq.producer.Message')
    def test_send_msg(self, Message, Container, TimeoutHandler):
        self.producer.through_queue('test-queue')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        props = {'prop1': 'foo', 'prop2': 'bar'}
        body = 'this is a test'
        with self.producer as prod:
            prod.send_msg(props, body)
        Message.assert_called_once_with(properties=props, body=body)

    @patch('rhmsg.activemq.producer.TimeoutHandler', autospec=True)
    @patch('rhmsg.activemq.producer.Container', autospec=True)
    @patch('rhmsg.activemq.producer.Message', autospec=True)
    def test_send_msg_with_kws(self, Message, Container, TimeoutHandler):
        """
        Test that keyword args passed to send_msg() get passed through as
        attributes on the underlying Message object.
        """
        Container.return_value.error_msgs = []
        self.producer.through_queue('test-queue')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        props = {'prop1': 'foo', 'prop2': 'bar'}
        body = 'this is a test'
        with self.producer as prod:
            prod.send_msg(props, body,
                          reply_to='topic://test.topic',
                          correlation_id='a1b2c3')
        Message.assert_called_once_with(properties=props, body=body)
        msg = Message.return_value
        self.assertEqual(msg.reply_to, 'topic://test.topic')
        self.assertEqual(msg.correlation_id, 'a1b2c3')

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    @patch('rhmsg.activemq.producer.Message')
    def test_send_msg_fail(self, Message, Container, TimeoutHandler):
        self.producer.through_queue('test-queue')
        props = {'prop1': 'foo', 'prop2': 'bar'}
        body = 'this is a test'
        with self.assertRaisesRegex(
                RuntimeError,
                '^could not send 1 message to any destinations, errors:\n$'):
            with self.producer as prod:
                prod.send_msg(props, body)

    @patch.dict(PRODUCER_CONFIG, timeout=10)
    def test_timeout(self):
        producer = AMQProducer(**PRODUCER_CONFIG)
        with producer as prod:
            self.assertEquals(prod.conf['connect_timeout'], 10)
            self.assertEquals(prod.conf['send_timeout'], 10)

    @patch.dict(PRODUCER_CONFIG, urls=None, host='host.example.com')
    def test_url_host(self):
        producer = AMQProducer(**PRODUCER_CONFIG)
        self.assertEqual(producer.urls, ['amqps://host.example.com:5671'])

    @patch.dict(PRODUCER_CONFIG, urls=None, host='host.example.com', port=5672)
    def test_url_host_port(self):
        producer = AMQProducer(**PRODUCER_CONFIG)
        self.assertEqual(producer.urls, ['amqps://host.example.com:5672'])

    @patch.dict(PRODUCER_CONFIG, urls=None)
    def test_url_none(self):
        with self.assertRaisesRegex(RuntimeError, '^either host or urls must be specified$'):
            AMQProducer(**PRODUCER_CONFIG)

    @patch.dict(PRODUCER_CONFIG, urls='amqps://amq.example.com:5671')
    def test_url_str(self):
        producer = AMQProducer(**PRODUCER_CONFIG)
        self.assertTrue(isinstance(producer.urls, list))

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    @patch('rhmsg.activemq.producer.Message')
    def test_send_msgs(self, Message, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        msgs = [({'testheader': 1}, '"test body 1"'),
                ({'testheader': 2}, '"test body 2"'),
                ({'testheader': 3}, '"test body 3"')]
        with self.producer as prod:
            prod.send_msgs(msgs)
        self.assertEqual(Message.call_count, 3)

    @patch('rhmsg.activemq.producer.TimeoutHandler', autospec=True)
    @patch('rhmsg.activemq.producer.Container', autospec=True)
    @patch('rhmsg.activemq.producer.Message', autospec=True)
    def test_send_msgs_with_attrs(self, Message, Container, TimeoutHandler):
        Container.return_value.error_msgs = []
        self.producer.through_topic('test-topic')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        msgs = [({'testheader': 1}, '"test body 1"',
                 {'reply_to': 'topic://test.topic',
                  'correlation_id': 'a1b2c3'}),
                ({'testheader': 2}, '"test body 2"'),
                ({'testheader': 3}, '"test body 3"')]
        with self.producer as prod:
            prod.send_msgs(msgs)
        self.assertEqual(Message.call_count, 3)
        msg = Message.return_value
        self.assertEqual(msg.reply_to, 'topic://test.topic')
        self.assertEqual(msg.correlation_id, 'a1b2c3')

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    def test_send_no_context(self, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')
        msg = Mock()

        def clear_msgs(url, conf, msgs):
            self.assertEqual(msgs, [msg])
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        self.producer.send(msg)

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    @patch('rhmsg.activemq.producer.Message')
    def test_send_msg_no_context(self, Message, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        props = {'testheader': 1}
        body = '"test body"'
        self.producer.send_msg(props, body)
        Message.assert_called_once_with(properties=props, body=body)

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    @patch('rhmsg.activemq.producer.Message')
    def test_send_msgs_no_context(self, Message, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')

        def clear_msgs(url, conf, msgs):
            del msgs[:]
            return DEFAULT

        TimeoutHandler.side_effect = clear_msgs
        msgs = [({'testheader': 1}, '"test body 1"'),
                ({'testheader': 2}, '"test body 2"'),
                ({'testheader': 3}, '"test body 3"')]
        self.producer.send_msgs(msgs)
        self.assertEqual(Message.call_count, 3)

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    def test_send_error_handling(self, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')
        msg = Mock()
        with self.assertRaisesRegex(RuntimeError, '^could not send 1 message .*'):
            self.producer.send(msg)
        with self.assertRaisesRegex(RuntimeError, '^could not send 2 messages .*'):
            self.producer.send(msg, msg)

    @patch('rhmsg.activemq.producer.TimeoutHandler')
    @patch('rhmsg.activemq.producer.Container')
    def test_send_error_handling_msgs(self, Container, TimeoutHandler):
        self.producer.through_topic('test-topic')
        msg = Mock()

        Container.return_value.error_msgs = [('amqp://broker1.example.com', 'err1', 'desc1')]
        with six.assertRaisesRegex(self,
                                   RuntimeError,
                                   r'\namqp://broker1.example.com: err1: desc1$') as cm:
            self.producer.send(msg)
        # The exception message should have one intro line, and one error line for
        # each entry in error_msgs for each Container we create.
        self.assertEqual(len(str(cm.exception).splitlines()), 3)

        Container.return_value.error_msgs.append(('amqp://broker2.example.com', 'err2', 'desc2'))
        with six.assertRaisesRegex(self,
                                   RuntimeError,
                                   r'\namqp://broker1.example.com: err1: desc1'
                                   r'\namqp://broker2.example.com: err2: desc2$') as cm:
            self.producer.send(msg)
        self.assertEqual(len(str(cm.exception).splitlines()), 5)


class TestTimeoutHandler(unittest.TestCase):
    def setUp(self):
        self.handler = TimeoutHandler('amqps://amq1.example.com:5671', HANDLER_CONFIG, [])

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_start(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        event.container.connect.assert_called_once_with(url='amqps://amq1.example.com:5671',
                                                        reconnect=False,
                                                        ssl_domain=SSLDomain.return_value)
        self.assertEqual(event.container.schedule.call_count, 2)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_timer_task(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.assertTrue(self.handler.timeout_task is not None)
        self.handler.on_timer_task(event)
        event.container.schedule.return_value.cancel.assert_called_once_with()
        self.assertTrue(self.handler.timeout_task is None)
        event.container.stop.assert_called_once_with()
        event.container.stop.reset_mock()
        self.handler.log = Mock()
        event.container.connected = True
        self.handler.on_timer_task(event)
        event.container.stop.assert_called_once_with()
        self.assertTrue(self.handler.log.error.call_args[0][0].startswith('send timeout expired'))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_connection_opened(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.assertTrue(self.handler.connect_task is not None)
        self.handler.on_connection_opened(event)
        self.assertTrue(event.container.connected)
        event.container.schedule.return_value.cancel.assert_called_once_with()
        self.assertTrue(self.handler.connect_task is None)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_send_msgs(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        msg = Mock(properties={'testheader': 1}, body='"test body"')
        self.handler.msgs = [msg]
        self.handler.on_connection_opened(event)
        event.container.create_sender.assert_called_once_with(event.connection,
                                                              target='topic://test-topic')
        sender = event.container.create_sender.return_value
        sender.send.assert_called_once_with(msg)
        sender.close.assert_called_once_with()

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_update_pending(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.msgs = [Mock(properties={'testheader': 1}, body='"test body"'),
                             Mock(properties={'testheader': 2}, body='"test body"')]
        delivery0 = Mock()
        delivery1 = Mock()
        sender = event.container.create_sender.return_value
        sender.send.side_effect = [delivery0, delivery1]
        log = Mock()
        self.handler.log = log
        self.handler.on_connection_opened(event)
        self.assertEqual(len(self.handler.pending), 2)
        event.delivery = delivery0
        self.handler.update_pending(event)
        self.assertEqual(len(self.handler.pending), 1)
        self.assertTrue(delivery0 not in self.handler.pending)
        log.debug.call_args[0][0].startswith('removed message')
        event.delivery = delivery1
        self.handler.update_pending(event)
        self.assertEqual(len(self.handler.pending), 0)
        self.assertTrue(delivery0 not in self.handler.pending)
        log.error.call_args[0][0].startswith('2 messages unsent')
        sender.close.assert_called_once_with()
        self.assertEqual(event.container.schedule.return_value.cancel.call_count, 2)
        event.connection.close.assert_called_once_with()

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_settled(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.msgs = [Mock(properties={'testheader': 1}, body='"test body"')]
        self.handler.on_connection_opened(event)
        delivery = event.container.create_sender.return_value.send.return_value
        self.assertTrue(delivery in self.handler.pending)
        event.delivery = delivery
        self.handler.on_settled(event)
        self.assertEqual(len(self.handler.msgs), 0)
        self.assertEqual(len(self.handler.pending), 0)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_rejected(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.msgs = [Mock(properties={'testheader': 1}, body='"test body"')]
        self.handler.on_connection_opened(event)
        delivery = event.container.create_sender.return_value.send.return_value
        self.assertTrue(delivery in self.handler.pending)
        event.delivery = delivery
        self.handler.on_rejected(event)
        self.assertEqual(len(self.handler.msgs), 1)
        self.assertEqual(len(self.handler.pending), 0)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_released(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.msgs = [Mock(properties={'testheader': 1}, body='"test body"')]
        self.handler.on_connection_opened(event)
        delivery = event.container.create_sender.return_value.send.return_value
        self.assertTrue(delivery in self.handler.pending)
        event.delivery = delivery
        self.handler.on_released(event)
        self.assertEqual(len(self.handler.msgs), 1)
        self.assertEqual(len(self.handler.pending), 0)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_transport_tail_closed(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.assertTrue(self.handler.connect_task is not None)
        self.assertTrue(self.handler.timeout_task is not None)
        self.handler.on_transport_tail_closed(event)
        self.assertEqual(event.container.schedule.return_value.cancel.call_count, 2)
        self.assertTrue(self.handler.connect_task is None)
        self.assertTrue(self.handler.timeout_task is None)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_handle_error_no_endpoint(self, SSLDomain):
        event = Mock()
        event.foo = None
        self.handler.on_start(event)
        self.handler.handle_error('foo', event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'foo error', 'unspecified'))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_handle_error_endpoint_no_condition(self, SSLDomain):
        event = Mock()
        event.foo.remote_condition = None
        event.foo.condition = None
        self.handler.on_start(event)
        self.handler.handle_error('foo', event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'foo error', 'unspecified'))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_handle_error_endpoint_condition(self, SSLDomain):
        event = Mock()
        event.foo.remote_condition = None
        self.handler.on_start(event)
        self.handler.handle_error('foo', event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0], (self.handler.url,
                                                         event.foo.condition.name,
                                                         event.foo.condition.description))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_handle_error_endpoint_remote_condition(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.handle_error('foo', event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0], (self.handler.url,
                                                         event.foo.remote_condition.name,
                                                         event.foo.remote_condition.description))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_connection_error_no_endpoint(self, SSLDomain):
        event = Mock()
        event.connection = None
        self.handler.on_start(event)
        self.handler.on_connection_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'connection error', 'unspecified'))

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_connection_error(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.on_connection_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url,
                          event.connection.remote_condition.name,
                          event.connection.remote_condition.description))
        self.assertFalse(event.connection.close.called)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_session_error_no_endpoint(self, SSLDomain):
        event = Mock()
        event.session = None
        self.handler.on_start(event)
        self.handler.on_session_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'session error', 'unspecified'))
        self.assertFalse(event.connection.close.called)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_session_error(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.on_session_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url,
                          event.session.remote_condition.name,
                          event.session.remote_condition.description))
        self.assertFalse(event.connection.close.called)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_link_error_no_endpoint(self, SSLDomain):
        event = Mock()
        event.link = None
        self.handler.on_start(event)
        self.handler.on_link_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'link error', 'unspecified'))
        event.connection.close.assert_called_once_with()

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_link_error(self, SSLDomain):
        event = Mock()
        self.handler.on_start(event)
        self.handler.on_link_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0], (self.handler.url,
                                                         event.link.remote_condition.name,
                                                         event.link.remote_condition.description))
        event.connection.close.assert_called_once_with()

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_transport_error_no_endpoint(self, SSLDomain):
        event = Mock()
        event.transport = None
        self.handler.on_start(event)
        self.handler.on_transport_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0],
                         (self.handler.url, 'transport error', 'unspecified'))
        self.assertFalse(event.connection.close.called)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_transport_error_no_close(self, SSLDomain):
        event = Mock()
        event.transport.remote_condition = None
        self.handler.on_start(event)
        self.handler.on_transport_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0], (self.handler.url,
                                                         event.transport.condition.name,
                                                         event.transport.condition.description))
        self.assertFalse(event.connection.close.called)

    @patch('rhmsg.activemq.producer.SSLDomain')
    def test_on_transport_error_close(self, SSLDomain):
        event = Mock()
        event.transport.remote_condition = None
        event.transport.condition.name = 'amqp:unauthorized-access'
        self.handler.on_start(event)
        self.handler.on_transport_error(event)
        self.assertEqual(len(event.container.error_msgs), 1)
        self.assertEqual(event.container.error_msgs[0], (self.handler.url,
                                                         event.transport.condition.name,
                                                         event.transport.condition.description))
        event.connection.close.assert_called_once_with()
