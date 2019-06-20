# -*- coding: utf-8 -*-

import os
import json
import tempfile

import rhmsg.cli.replay as replay

from mock import Mock
from mock import patch

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class TestGrepMessages(unittest.TestCase):
    """Test grep_messages"""

    def setUp(self):
        self.fake_server_url = 'http://localhost/'
        self.fake_msg_id = 'fake-id'
        self.fake_msg = {
            'msg_id': self.fake_msg_id,
            'msg': {
                "build": {
                    "id": 562101,
                    "nvr": "openshift-ansible-3.3.1.32-1.git.0.3b74dea.el7",
                }
            }
        }

    @patch('rhmsg.cli.replay.requests.get')
    def test_raise_error_if_non_200(self, get):
        get.return_value.status_code = 500
        get.return_value.content = 'Internal server error'

        self.assertRaisesRegex(RuntimeError, 'Internal server error',
                               replay.grep_messages, self.fake_server_url, self.fake_msg_id)

    def test_not_verify_ssl(self):
        with patch('rhmsg.cli.replay.requests.get') as get:
            get.return_value.status_code = 200

            replay.grep_messages(self.fake_server_url, self.fake_msg_id)
            get.assert_called_once_with(
                '{0}/id?id={1}&is_raw=true&size=extra-large'.format(
                    self.fake_server_url.strip('/'), self.fake_msg_id),
                verify=True)

        with patch('rhmsg.cli.replay.requests.get') as get:
            get.return_value.status_code = 200

            replay.grep_messages(self.fake_server_url, self.fake_msg_id, verify_ssl=False)
            get.asssert_called_once_with(
                '{0}/id?id={1}&is_raw=true&size=extra-large'.format(
                    self.fake_server_url.strip('/'), self.fake_msg_id),
                verify=False)

    @patch('rhmsg.cli.replay.requests.get')
    def test_grep_message_by_id(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = self.fake_msg

        msg = replay.grep_messages(self.fake_server_url, self.fake_msg_id)

        self.assertEqual(self.fake_msg, msg)


class TestReplayMessages(unittest.TestCase):
    """Test replay_messages"""

    @patch('rhmsg.cli.replay.AMQProducer.__enter__')
    def test_send_message(self, __enter__):
        __enter__.return_value = Mock()

        fake_msg = {
            'msg_id': 'fake-msg-id',
            'msg': {
                "build": {
                    "id": 562101,
                    "nvr": "openshift-ansible-3.3.1.32-1.git.0.3b74dea.el7",
                }
            }
        }

        replay.replay_messages(fake_msg, ['localhost:61612'], 'fake.topic',
                               'fake_cert', 'fake_private_key', 'fake_ca_certs')

        __enter__.return_value.send.assert_called_once()

        messages, _ = __enter__.return_value.send.call_args
        self.assertEqual(1, len(messages))

        msg = messages[0]
        self.assertEqual('Replay fake-msg-id', msg.subject)
        self.assertEqual(json.dumps(fake_msg), msg.body)


class TestLoadMessagesFromFile(unittest.TestCase):
    """Test load_messages_from_file"""

    def setUp(self):
        self.fd, self.message_file = tempfile.mkstemp(
            prefix='rhsmg-test-msg-file-')

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.message_file)

    def test_load_multiple_messages(self):
        fake_messages = [
            {
                'msg_id': 'msg-id-0',
                'msg': {
                    'sighash': '2e31f3df8dc038e31ece5d6603b18de6',
                    'sigkey': '',
                    'rpm': {
                        'build_id': 565062,
                        'name': 'jbcs-openssl-dist',
                        'version': '1.0.2h',
                        'release': '2.jbcs.el7',
                    },
                    'build': {
                        'build_id': 565062,
                        'version': '1.0.2h',
                        'nvr': 'jbcs-openssl-dist-1.0.2h-2.jbcs.el7',
                        'name': 'jbcs-openssl-dist',
                        'release': '2.jbcs.el7'
                    }
                }
            },
            {
                'msg_id': 'msg-id-1',
                'msg': {
                    'sighash': '2e9d4b5214c94508be559a9af4c3f347',
                    'sigkey': '',
                    'rpm': {
                        'build_id': 565062,
                        'name': 'jbcs-openssl-dist',
                        'version': '1.0.2h',
                        'release': '2.jbcs.el7',
                    },
                    'build': {
                        'build_id': 565062,
                        'version': '1.0.2h',
                        'nvr': 'jbcs-openssl-dist-1.0.2h-2.jbcs.el7',
                        'name': 'jbcs-openssl-dist',
                        'release': '2.jbcs.el7'
                    }
                }
            },
        ]

        for msg in fake_messages:
            os.write(self.fd, json.dumps(msg).encode('utf-8'))
            os.write(self.fd, '\n'.encode('utf-8'))

        msgs = list(replay.load_messages_from_file(self.message_file,
                                                   multiple_messages=True))

        self.assertEqual(len(fake_messages), len(msgs))
        self.assertEqual(fake_messages, msgs)

    def test_load_one_message(self):
        fake_message = {
            'msg_id': 'msgid',
            'msg': {
                'sighash': '2e31f3df8dc038e31ece5d6603b18de6',
                'sigkey': '',
                'rpm': {
                    'build_id': 565062,
                    'name': 'jbcs-openssl-dist',
                    'version': '1.0.2h',
                    'release': '2.jbcs.el7',
                },
                'build': {
                    'build_id': 565062,
                    'version': '1.0.2h',
                    'nvr': 'jbcs-openssl-dist-1.0.2h-2.jbcs.el7',
                    'name': 'jbcs-openssl-dist',
                    'release': '2.jbcs.el7'
                }
            }
        }

        os.write(self.fd, json.dumps(fake_message).encode('utf-8'))
        msgs = list(replay.load_messages_from_file(self.message_file))

        self.assertEqual(1, len(msgs))
        self.assertEqual(msgs[0], fake_message)
