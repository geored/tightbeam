# -*- coding: utf-8 -*-

from __future__ import absolute_import

import proton
import os
import six

import logging

from optparse import OptionParser

from rhmsg.activemq.producer import AMQProducer
from .envs import broker_envs


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('producer')


def build_command_line_parser():
    parser = OptionParser()
    parser.add_option('-e', '--env', choices=list(broker_envs.keys()),
                      default='dev', help='Environment to connect to (default: %default)')
    parser.add_option('-d', '--debug', dest='debug', action='store_true',
                      help='Output more information for debug')
    parser.add_option('--certificate-file', dest='cert_file',
                      help='Certificate file')
    parser.add_option('--private-key-file', dest='private_key_file',
                      help='Private Key file')
    parser.add_option('--ca-certs', dest='ca_certs', default='/etc/pki/tls/certs/ca-bundle.crt',
                      help='Trusted CA certificate bundle (default: %default)')
    parser.add_option('--queue', dest='producer_queue',
                      help='Queue to send messages.')
    parser.add_option('--topic', dest='producer_topic',
                      help='Topic to send messages.')
    parser.add_option('--subject', dest='subject',
                      default='amqproducer: hello',
                      help="Message's subject")
    parser.add_option('--property', action='append', dest='properties',
                      help='Property')

    return parser


def produce_message(options, args):
    producer_config = {
        'urls': broker_envs[options.env],
        'certificate': options.cert_file,
        'private_key': options.private_key_file,
        'trusted_certificates': options.ca_certs,
        }

    if options.properties:
        properties = dict((prop.split('=', 1) for prop in options.properties))
    else:
        properties = {}

    with AMQProducer(**producer_config) as producer:
        if options.producer_queue:
            producer.through_queue(options.producer_queue)
        if options.producer_topic:
            producer.through_topic(options.producer_topic)

        message = proton.Message()
        message.body = ' '.join(args)
        if isinstance(message.body, six.binary_type):
            # On python2, convert to unicode
            message.body = message.body.decode('utf-8', 'replace')
        message.properties = properties.copy()
        message.subject = options.subject
        producer.send(message)


def main():
    try:
        parser = build_command_line_parser()
        options, args = parser.parse_args()

        if options.debug:
            os.environ['PN_TRACE_FRM'] = '1'

        produce_message(options, args)
    except KeyboardInterrupt:
        pass
