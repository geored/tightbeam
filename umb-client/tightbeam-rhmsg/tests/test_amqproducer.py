# tests for the rhmsg.cli.amqproducer module

try:
    import unittest2 as unittest
except ImportError:
    import unittest
from mock import patch
import rhmsg.cli.amqproducer
import sys
import tempfile
import six


class TestAMQProducer(unittest.TestCase):

    @patch.object(sys, 'argv', new=['foo'])
    def test_ca_cert_default(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.ca_certs, '/etc/pki/tls/certs/ca-bundle.crt')

    @patch.object(sys, 'argv', new=['foo', '--ca-certs', '/tmp/certs.crt'])
    def test_ca_cert_custom(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.ca_certs, '/tmp/certs.crt')

    @patch.object(sys, 'argv', new=['foo'])
    def test_parser_env_default(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.env, 'dev')

    @patch.object(sys, 'argv', new=['foo', '--env', 'stage'])
    def test_parser_env_custom(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        self.assertEqual(opts.env, 'stage')

    # Silence noisy output from OptionParser
    @patch.object(sys, 'stderr', new=tempfile.TemporaryFile(mode='w+'))
    @patch.object(sys, 'argv', new=['foo', '--env', 'dummy'])
    def test_parser_env_invalid(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        with self.assertRaises(SystemExit):
            opts, args = parser.parse_args()

    @patch.object(sys, 'argv', new=['foo'])
    def test_produce_message_no_queue_topic(self):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        with self.assertRaises(AssertionError):
            rhmsg.cli.amqproducer.produce_message(opts, args)

    @patch.object(sys, 'argv', new=['foo', '--queue', 'test-queue'])
    @patch('rhmsg.cli.amqproducer.AMQProducer')
    def test_produce_message_queue(self, AMQProducer):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqproducer.produce_message(opts, args)
        prod = AMQProducer.return_value.__enter__.return_value
        prod.through_queue.assert_called_once_with('test-queue')

    @patch.object(sys, 'argv', new=['foo', '--topic', 'test-topic'])
    @patch('rhmsg.cli.amqproducer.AMQProducer')
    def test_produce_message_topic(self, AMQProducer):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqproducer.produce_message(opts, args)
        prod = AMQProducer.return_value.__enter__.return_value
        prod.through_topic.assert_called_once_with('test-topic')

    @patch.object(sys, 'argv', new=['foo', '--topic', 'test-topic', '--subject', 'subj', 'bar'])
    @patch('rhmsg.cli.amqproducer.proton.Message')
    @patch('rhmsg.cli.amqproducer.AMQProducer')
    def test_produce_message_send(self, AMQProducer, Message):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqproducer.produce_message(opts, args)
        prod = AMQProducer.return_value.__enter__.return_value
        msg = Message.return_value
        # Ensure we're always sending text in the body (unicode in python2 ad str in python3)
        self.assertFalse(isinstance(msg.body, six.binary_type))
        self.assertEqual(msg.body, u'bar')
        self.assertEqual(msg.subject, 'subj')
        prod.send.assert_called_once_with(msg)

    @patch.object(sys, 'argv', new=['foo', '--topic', 'test-topic',
                                    '--property', 'foo=bar=baz', 'bar'])
    @patch('rhmsg.cli.amqproducer.proton.Message')
    @patch('rhmsg.cli.amqproducer.AMQProducer')
    def test_allow_equality_sign_in_property_value(self, AMQProducer, Message):
        parser = rhmsg.cli.amqproducer.build_command_line_parser()
        opts, args = parser.parse_args()
        rhmsg.cli.amqproducer.produce_message(opts, args)
        msg = Message.return_value
        self.assertEqual({'foo': 'bar=baz'}, msg.properties)
