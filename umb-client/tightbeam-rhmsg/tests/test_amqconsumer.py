# tests for the rhmsg.cli.amqconsumer module

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import Mock, patch
import rhmsg.cli.amqconsumer
import sys
import tempfile


class TestAMQConsumer(unittest.TestCase):

    @patch.object(sys, 'argv', new=['foo'])
    def test_ca_cert_default(self):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.ca_certs, '/etc/pki/tls/certs/ca-bundle.crt')

    @patch.object(sys, 'argv', new=['foo', '--ca-certs', '/tmp/certs.crt'])
    def test_ca_cert_custom(self):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.ca_certs, '/tmp/certs.crt')

    @patch.object(sys, 'argv', new=['foo'])
    def test_parser_env_default(self):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.env, 'dev')

    @patch.object(sys, 'argv', new=['foo', '--env', 'stage'])
    def test_parser_env_custom(self):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.env, 'stage')

    # Silence noisy output from OptionParser
    @patch.object(sys, 'stderr', new=tempfile.TemporaryFile(mode='w+'))
    @patch.object(sys, 'argv', new=['foo', '--env', 'dummy'])
    def test_parser_env_invalid(self):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        with self.assertRaises(SystemExit):
            opts, args = parser.parse_args()

    # Work around python's different handling of sys.stdout, depending on
    # interactive terminal and LANG, so we can have a consistent test case.
    @patch.object(sys, 'stdout', new=tempfile.TemporaryFile(mode='w+'))
    def test_message_handler_unicode(self):
        props = {u'username': u'vkadlcik',
                 u'name': u'V\xe1clav Kadl\u010d\xedk'}
        body = u'{"username":"vkadlcik","name":"V\xe1clav Kadl\u010d\xedk"}'
        msg = Mock(properties=props, body=body)
        rhmsg.cli.amqconsumer.message_handler(
            msg, {'dump': False, 'pp': False,
                  'one_message_only': True, 'manual_ack': False})
        sys.stdout.seek(0)
        expected = """Got [02]: {0}\n""".format(body.encode('utf-8', 'backslashreplace'))
        self.assertEqual(expected, sys.stdout.read())

    @patch.object(sys, 'stdout', new=tempfile.TemporaryFile(mode='w+'))
    def test_message_handler_dump_unicode(self):
        props = {u'username': u'vkadlcik',
                 u'name': u'V\xe1clav Kadl\u010d\xedk'}
        body = u'{"username":"vkadlcik","name":"V\xe1clav Kadl\u010d\xedk"}'
        msg = Mock(properties=props, body=body,
                   id='abc123',
                   address='/topic/VirtualTopic.test',
                   subject='test',
                   durable=False,
                   content_type='text/json',
                   content_encoding='utf-8',
                   delivery_count=1,
                   reply_to=None,
                   priority=None)
        rhmsg.cli.amqconsumer.message_handler(
            msg, {'dump': True, 'pp': False,
                  'one_message_only': True, 'manual_ack': False})
        sys.stdout.seek(0)
        expected = """------------- (1) abc123 --------------
address: /topic/VirtualTopic.test
subject: test
properties: {0}
durable: False
content_type: text/json
content_encoding: utf-8
delivery_count: 1
reply_to: None
priority: None
body: {1}
""".format(props, body.encode('utf-8', 'backslashreplace'))
        self.assertEqual(expected, sys.stdout.read())

    @patch.object(sys, 'argv', new=['foo', '--address', 'queue://test-address'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_address(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        self.assertEqual(len(call_args), 1)
        self.assertEqual(call_args[0], 'queue://test-address')
        self.assertIsNone(call_opts.get('selector'))

    @patch.object(sys, 'argv', new=['foo', '--selector', 'foo == "bar"'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_selector(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        self.assertEqual(len(call_args), 1)
        self.assertIsNone(call_args[0])
        self.assertEqual(call_opts.get('selector'), 'foo == "bar"')

    @patch.object(sys, 'argv', new=['foo'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_all_off(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        data = {'dump': None,
                'pp': None,
                'one_message_only': False,
                'manual_ack': False}
        self.assertEqual(call_opts.get('data'), data)
        self.assertIn('subscription_name', call_opts)
        self.assertIsNone(call_opts['subscription_name'])

    @patch.object(sys, 'argv', new=['foo', '--dump', '--pp',
                                    '--one-message-only', '--manual-ack'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_all_on(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        data = {'dump': True,
                'pp': True,
                'one_message_only': True,
                'manual_ack': True}
        self.assertEqual(call_opts.get('data'), data)

    @patch.object(sys, 'argv', new=['foo', '--address', 'queue://test-address',
                                    '--durable'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_durable(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        self.assertIn('subscription_name', call_opts)
        self.assertEqual(call_opts['subscription_name'], opts.address)

    @patch.object(sys, 'argv', new=['foo', '--address', 'queue://test-address',
                                    '--durable', '--subscription-name', 'test-sub-name'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_durable_subscription_name(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        self.assertIn('subscription_name', call_opts)
        self.assertEqual(call_opts['subscription_name'], 'test-sub-name')

    @patch.object(sys, 'argv', new=['foo', '--address', 'queue://test-address',
                                    '--subscription-name', 'test-sub-name'])
    @patch('rhmsg.cli.amqconsumer.AMQConsumer')
    def test_consume_messages_options_subscription_name(self, AMQConsumer):
        parser = rhmsg.cli.amqconsumer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqconsumer.consume_messages(opts)
        cons = AMQConsumer.return_value
        self.assertEqual(cons.consume.call_count, 1)
        call_args, call_opts = cons.consume.call_args
        self.assertIn('subscription_name', call_opts)
        self.assertEqual(call_opts['subscription_name'], 'test-sub-name')
