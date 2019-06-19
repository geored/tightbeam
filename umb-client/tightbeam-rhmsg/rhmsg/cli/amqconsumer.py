# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

import itertools
import json
import os
import six

from optparse import OptionParser
from pprint import pprint

import logging

from rhmsg.activemq.consumer import AMQConsumer
from .envs import broker_envs

logging.basicConfig(level=logging.CRITICAL,
                    format='[%(levelname)s] %(message)s')
logger = logging.getLogger('Consumer')


def build_command_line_parser():
    parser = OptionParser()
    parser.add_option('-e', '--env', choices=list(broker_envs.keys()),
                      default='dev', help='Environment to connect to (default: %default)')
    parser.add_option('--address', dest='address',
                      help='Address which can be queue or topic')
    parser.add_option('--durable', action='store_true', help='Create a durable subscription')
    parser.add_option('--subscription-name', help='Use the specified name for the subscription, '
                      'otherwise it will be generated. Implies --durable.')
    parser.add_option('-d', '--debug', dest='debug', action='store_true',
                      help='Output more information for debug')
    parser.add_option('--certificate-file', dest='cert_file',
                      help='Certificate file')
    parser.add_option('--private-key-file', dest='private_key_file',
                      help='Private Key file')
    parser.add_option('--ca-certs', dest='ca_certs', default='/etc/pki/tls/certs/ca-bundle.crt',
                      help='Trusted CA certificate bundle (default: %default)')
    parser.add_option('--dump', action='store_true', dest='dump_message',
                      help='Dump message besides body.')
    parser.add_option('--selector', dest='selector', default=None)
    parser.add_option('--pp', dest='pretty_print', action='store_true',
                      help='Pretty-print received messages.')
    parser.add_option('--manual-ack', default=False, action='store_true',
                      help='Accept and ack received message manually.')
    parser.add_option('--one-message-only', default=False, action='store_true',
                      help='Only consume one message and exit.')

    return parser


counter = itertools.count(1)


def message_handler(message, data):
    num = six.next(counter)

    body = message.body
    if isinstance(body, six.text_type):
        body = body.encode('utf-8', 'backslashreplace')
    if data['dump']:
        print('------------- ({0}) {1} --------------'.format(num, message.id))
        print('address:', message.address)
        print('subject:', message.subject)
        print('properties:', message.properties)
        print('durable:', message.durable)
        print('content_type:', message.content_type)
        print('content_encoding:', message.content_encoding)
        print('delivery_count:', message.delivery_count)
        print('reply_to:', message.reply_to)
        print('priority:', message.priority)
        if data['pp']:
            print('body:')
            pprint(json.loads(body))
        else:
            print('body:', body)
    else:
        if data['pp']:
            print('Got [%02d]:' % num)
            pprint(json.loads(body))
        else:
            print('Got [%02d]:' % num, body)

    return data['one_message_only'], not data['manual_ack']


def consume_messages(options):
    consumer_config = {
        'urls': broker_envs[options.env],
        'certificate': options.cert_file,
        'private_key': options.private_key_file,
        'trusted_certificates': options.ca_certs,
        }
    if options.durable and not options.subscription_name:
        options.subscription_name = options.address
    consumer = AMQConsumer(**consumer_config)
    consumer.consume(options.address,
                     selector=options.selector,
                     callback=message_handler,
                     auto_accept=False,
                     subscription_name=options.subscription_name,
                     data={'dump': options.dump_message,
                           'pp': options.pretty_print,
                           'one_message_only': options.one_message_only,
                           'manual_ack': options.manual_ack,
                           })


def main():
    try:
        parser = build_command_line_parser()
        options, args = parser.parse_args()

        if options.debug:
            os.environ['PN_TRACE_FRM'] = '1'

        consume_messages(options)
    except KeyboardInterrupt:
        pass
