# -*- coding: utf-8 -*-

"""
Get UMB messages from internal datagrepper and send it to given broker.
"""

from __future__ import absolute_import

import json
import os
import logging
import requests
import proton

from optparse import OptionParser
from optparse import OptionGroup

from rhmsg.activemq.producer import AMQProducer
from .envs import broker_envs

logging.basicConfig(level=logging.CRITICAL,
                    format='[%(levelname)s] %(message)s')
logger = logging.getLogger('replay')


class InvalidMessageError(Exception):
    def __init__(self, raw, line_no):
        self.raw = raw
        self.line_no = line_no

    def __str__(self):
        return 'Cannot decode message from file at line {0}.'.format(self.line_no)

    def __repr__(self):
        return '<{0}: at line {1}>'.format(self.__class__.__name__, self.line_no)


def build_command_line_parser():
    parser = OptionParser(
        description='Read unified messages from datagrepper or a file '
                    'replay to unified message bus. If no file is specified, '
                    'messages will be retreived from datagrepper.')
    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False,
                      help='Output more information for debug')

    datagrepper_group = OptionGroup(parser, 'DATAGREPPER options',
                                    'From where to retreive old messages.')
    datagrepper_group.add_option('--server-url', dest='server_url',
                                 help='Server URL of DATAGREPPER. Example: http://hostname[:port]/')
    datagrepper_group.add_option('--no-ssl-verify', dest='no_ssl_verify', action='store_true',
                                 help='Do not verify SSL.')
    parser.add_option_group(datagrepper_group)

    msgfile_group = OptionGroup(parser, 'File options',
                                'Read message from file. Each message in that file should be a '
                                'string that can be decoded into a JSON object.')
    msgfile_group.add_option('-f', '--file', metavar='FILE', dest='msg_file',
                             help='File containing message to replay.')
    msgfile_group.add_option('-m', '--multiple-lines', dest='multiple_lines',
                             action='store_true', default=False,
                             help='Indicate file contains multiple messages line by line.')
    parser.add_option_group(msgfile_group)

    broker_group = OptionGroup(parser, 'Message broker options',
                               'Send grepped messages to this broker to replay them.')
    broker_group.add_option('-e', '--env', choices=list(broker_envs.keys()), default='dev',
                            help='Environment to connect to. Valid choices: {} '
                                 '(default: %default)'.format(', '.join(broker_envs.keys())))
    broker_group.add_option('--address', dest='address',
                            help='Address which can be queue or topic')
    broker_group.add_option('--certificate-file', dest='cert_file',
                            help='Certificate file')
    broker_group.add_option('--private-key-file', dest='private_key_file',
                            help='Private Key file')
    broker_group.add_option('--ca-certs', dest='ca_certs',
                            default='/etc/pki/tls/certs/ca-bundle.crt',
                            help='Trusted CA certificate bundle (default: %default)')
    parser.add_option_group(broker_group)

    return parser


def check_command_line(parser, options, args):
    if options.msg_file:
        if not os.path.exists(options.msg_file):
            parser.error('Message file {0} does not exist.'.format(options.msg_file))
    else:
        if len(args) == 0:
            parser.error('You have to give at least one message ID.')
        if not options.server_url:
            parser.error('Missing --server-url.')

    if not options.address:
        parser.error('Missing --address.')
    if not options.cert_file:
        parser.error('Missing --certificate-file.')
    if not options.private_key_file:
        parser.error('Missing --private-key-file.')


def grep_messages(server_url, msg_id, verify_ssl=True):
    url = '{0}/id?id={1}&is_raw=true&size=extra-large'.format(server_url.strip('/'), msg_id)
    response = requests.get(url, verify=verify_ssl)
    if response.status_code != 200:
        raise RuntimeError(response.content)
    return response.json()


def load_messages_from_file(filename, multiple_messages=False):
    with open(filename, 'r') as fin:
        if multiple_messages:
            for line_no, line in enumerate(fin, 1):
                try:
                    data = json.loads(line)
                except (ValueError, TypeError):
                    raise InvalidMessageError(line.strip(), line_no)
                else:
                    yield data
        else:
            yield json.loads(fin.read())


def replay_messages(msg, broker_urls, topic, cert_file, private_key_file, ca_certs):
    producer_config = {
        'urls': broker_urls,
        'certificate': cert_file,
        'private_key': private_key_file,
        'trusted_certificates': ca_certs,
        }

    with AMQProducer(**producer_config) as producer:
        producer.through_topic(topic)

        message = proton.Message()
        message.subject = 'Replay {0}'.format(msg['msg_id'])
        message.body = json.dumps(msg)

        producer.send(message)


def main():
    parser = build_command_line_parser()
    options, msg_ids = parser.parse_args()

    check_command_line(parser, options, msg_ids)

    if options.debug:
        os.environ['PN_TRACE_FRM'] = '1'

    if options.msg_file:
        msgs = load_messages_from_file(options.msg_file)
    else:
        msgs = [grep_messages(options.server_url,
                              msg_id,
                              verify_ssl=not options.no_ssl_verify)
                for msg_id in msg_ids]

    for msg in msgs:
        replay_messages(msg=msg,
                        broker_urls=broker_envs[options.env],
                        topic=options.address,
                        cert_file=options.cert_file,
                        private_key_file=options.private_key_file,
                        ca_certs=options.ca_certs)
