# tests for the AMQConsumer class

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import call, patch, Mock, ANY
from rhmsg.activemq.consumer import AMQConsumer
from rhmsg.activemq.consumer import ReceiverHandler
from proton.reactor import DurableSubscription, Selector

CONSUMER_CONFIG = {
    'urls': [
        'amqps://amq1.example.com:5671',
        'amqps://amq2.example.com:5671'
    ],
    'certificate': 'cert',
    'private_key': 'key',
    'trusted_certificates': 'trusted_certs'
}


class TestConsumer(unittest.TestCase):

    @patch('rhmsg.activemq.consumer.SSLDomain', autospec=True)
    def test_ssl_domain(self, SSLDomain):
        consumer = AMQConsumer(**CONSUMER_CONFIG)
        SSLDomain.assert_called_once_with(SSLDomain.MODE_CLIENT)
        ssl_domain = consumer.ssl_domain
        ssl_domain.set_credentials.assert_called_once_with(
            CONSUMER_CONFIG['certificate'],
            CONSUMER_CONFIG['private_key'],
            None)
        ssl_domain.set_trusted_ca_db.assert_called_once_with(
            CONSUMER_CONFIG['trusted_certificates'])
        ssl_domain.set_peer_authentication.assert_called_once_with(
            SSLDomain.VERIFY_PEER)

    @patch('rhmsg.activemq.consumer.SSLDomain', autospec=True)
    @patch('rhmsg.activemq.consumer.Container')
    @patch('rhmsg.activemq.consumer.ReceiverHandler')
    def test_run_container_to_consume(
            self, ReceiverHandler, Container, SSLDomain):
        consumer = AMQConsumer(**CONSUMER_CONFIG)
        message_handler = Mock()
        consumer.consume('myqueue', message_handler)

        Container.assert_called_once_with(ReceiverHandler.return_value)
        Container.return_value.run.assert_called_once()

    def test_handle_one_message_and_return(self):
        message_handler = Mock()
        message_handler.return_value = 'result'

        handler = ReceiverHandler(CONSUMER_CONFIG['urls'],
                                  'myqueue',
                                  message_handler)
        event = Mock(message='hello world')
        handler.on_message(event)

        message_handler.assert_has_calls([call('hello world', None)])
        event.connection.close.assert_called_once()
        self.assertEqual('result', handler.result)

    def test_handle_messages_continuously(self):
        message_handler = Mock(side_effect=[None, None, 'result'])

        handler = ReceiverHandler(CONSUMER_CONFIG['urls'],
                                  'myqueue',
                                  message_handler)

        events = [Mock(message='hello'),
                  Mock(message='world'),
                  Mock(message='!')]
        [handler.on_message(event) for event in events]

        calls = [call(event.message, None) for event in events]
        message_handler.assert_has_calls(calls)
        events[-1].connection.close.assert_called_once()
        self.assertEqual('result', handler.result)


class TestManualAck(unittest.TestCase):
    """Test manual ack that is enabled by passing False to auto_accept"""

    def test_fail_if_callback_not_return_a_tuple(self):

        def message_handler(message, data):
            return None

        handler = ReceiverHandler(CONSUMER_CONFIG['urls'],
                                  'myqueue',
                                  message_handler,
                                  auto_accept=False)
        event = Mock()
        self.assertRaises(ValueError, handler.on_message, event)

    @patch('rhmsg.activemq.consumer.ReceiverHandler.accept')
    def test_accept_message(self, accept):

        def message_handler(message, data):
            return False, True

        handler = ReceiverHandler(CONSUMER_CONFIG['urls'],
                                  'myqueue',
                                  message_handler,
                                  auto_accept=False)
        event = Mock()
        handler.on_message(event)

        accept.assert_called_once_with(event.delivery)

    @patch('rhmsg.activemq.consumer.ReceiverHandler.accept')
    @patch('rhmsg.activemq.consumer.ReceiverHandler.release')
    def test_not_accept_message(self, release, accept):

        def message_handler(message, data):
            return False, False

        handler = ReceiverHandler(CONSUMER_CONFIG['urls'],
                                  'myqueue',
                                  message_handler,
                                  auto_accept=False)
        event = Mock()
        handler.on_message(event)

        accept.assert_not_called()
        release.assert_called_once_with(event.delivery, delivered=True)


class TestDurableSubscriptions(unittest.TestCase):
    @patch('rhmsg.activemq.consumer.SSLDomain', autospec=True)
    @patch('rhmsg.activemq.consumer.Container', autospec=True)
    @patch('rhmsg.activemq.consumer.ReceiverHandler', autospec=True)
    def test_consume_no_sub_name(self, ReceiverHandler, Container, SSLDomain):
        """Test creation of a ReceiverHandler when there is no subscription_name
        provided."""
        handler = ReceiverHandler.return_value
        handler.result = 'foo'
        consumer = AMQConsumer(**CONSUMER_CONFIG)
        consumer.consume('myqueue', Mock())
        self.assertEqual(ReceiverHandler.call_count, 1)
        kwargs = ReceiverHandler.call_args[1]
        self.assertIn('subscription_name', kwargs)
        self.assertIsNone(kwargs['subscription_name'])

    @patch('rhmsg.activemq.consumer.SSLDomain', autospec=True)
    @patch('rhmsg.activemq.consumer.Container', autospec=True)
    @patch('rhmsg.activemq.consumer.ReceiverHandler', autospec=True)
    def test_consume_sub_name(self, ReceiverHandler, Container, SSLDomain):
        """Test creation of a ReceiverHandler when there is a subscription_name
        provided."""
        handler = ReceiverHandler.return_value
        handler.result = 'foo'
        consumer = AMQConsumer(**CONSUMER_CONFIG)
        consumer.consume('myqueue', Mock(), subscription_name='test-sub')
        self.assertEqual(ReceiverHandler.call_count, 1)
        kwargs = ReceiverHandler.call_args[1]
        self.assertIn('subscription_name', kwargs)
        self.assertEqual(kwargs['subscription_name'], 'test-sub')

    def test_on_start_no_sub_name(self):
        """Test the behavior of the on_start() handler when there is no subscription_name
        provided (a non-durable subscription)."""
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', Mock())
        event = Mock()
        handler.on_start(event)
        event.container.connect.assert_called_once_with(urls=CONSUMER_CONFIG['urls'],
                                                        ssl_domain=None,
                                                        heartbeat=500)
        conn = event.container.connect.return_value
        event.container.create_receiver.assert_called_once_with(conn, 'test-topic',
                                                                name=None,
                                                                options=[])

    def test_on_start_sub_name(self):
        """Test the behavior of the on_start() handler when there is a subscription_name
        provided (a durable subscription)."""
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', Mock(),
                                  subscription_name='test-sub')
        event = Mock()
        handler.on_start(event)
        event.container.container_id == 'test-sub'
        event.container.connect.assert_called_once_with(urls=CONSUMER_CONFIG['urls'],
                                                        ssl_domain=None,
                                                        heartbeat=500)
        conn = event.container.connect.return_value
        event.container.create_receiver.assert_called_once_with(conn, 'test-topic',
                                                                name='test-sub',
                                                                options=ANY)
        kwargs = event.container.create_receiver.call_args[1]
        opts = kwargs['options']
        self.assertEqual(len(opts), 1)
        self.assertIsInstance(opts[0], DurableSubscription)

    def test_on_start_sub_name_and_selector(self):
        """Test the behavior of the on_start() handler when there is a subscription_name
        provided (a durable subscription) and a selector."""
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', Mock(),
                                  subscription_name='test-sub',
                                  selector='foo = "bar"')
        event = Mock()
        handler.on_start(event)
        event.container.container_id == 'test-sub'
        event.container.connect.assert_called_once_with(urls=CONSUMER_CONFIG['urls'],
                                                        ssl_domain=None,
                                                        heartbeat=500)
        conn = event.container.connect.return_value
        event.container.create_receiver.assert_called_once_with(conn, 'test-topic',
                                                                name='test-sub',
                                                                options=ANY)
        kwargs = event.container.create_receiver.call_args[1]
        opts = kwargs['options']
        self.assertEqual(len(opts), 2)
        self.assertIsInstance(opts[0], Selector)
        self.assertIsInstance(opts[1], DurableSubscription)

    def test_on_message_close_callback_returns_none(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns None."""
        callback = Mock(return_value=None)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback)
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_not_called()

    def test_on_message_close_callback_returns_not_none(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns something besides None."""
        callback = Mock(return_value='foo')
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback)
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_called_once_with()
        event.connection.close.assert_called_once_with()

    def test_on_message_close_callback_returns_false(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns False."""
        callback = Mock(return_value=False)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback)
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_not_called()

    def test_on_message_close_callback_returns_true(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns True."""
        callback = Mock(return_value=True)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback)
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_called_once_with()
        event.connection.close.assert_called_once_with()

    def test_on_message_close_callback_returns_none_with_sub_name(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns None and there is a subscription_name (a durable subscription)."""
        callback = Mock(return_value=None)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback,
                                  subscription_name='test-sub')
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_not_called()

    def test_on_message_close_callback_returns_not_none_with_sub_name(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns something besides None and there is a subscription_name
        (a durable subscription)."""
        callback = Mock(return_value='foo')
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback,
                                  subscription_name='test-sub')
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_called_once_with()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_called_once_with()

    def test_on_message_close_callback_returns_false_with_sub_name(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns False and there is a subscription_name (a durable subscription)."""
        callback = Mock(return_value=False)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback,
                                  subscription_name='test-sub')
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_not_called()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_not_called()

    def test_on_message_close_callback_returns_true_with_sub_name(self):
        """Test the connection closing behavior of the on_message() handler when
        the callback returns True and there is a subscription_name (a durable subscription)."""
        callback = Mock(return_value=True)
        handler = ReceiverHandler(CONSUMER_CONFIG['urls'], 'test-topic', callback,
                                  subscription_name='test-sub')
        event = Mock()
        handler.on_message(event)
        event.receiver.detach.assert_called_once_with()
        event.receiver.close.assert_not_called()
        event.connection.close.assert_called_once_with()
