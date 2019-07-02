# -*- coding: utf-8 -*-

broker_envs = {
    'dev': [
        'amqps://messaging-devops-broker01.dev1.ext.devlab.redhat.com:5671',
        'amqps://messaging-devops-broker02.dev1.ext.devlab.redhat.com:5671'
    ],
    'qa': [
        'amqps://messaging-devops-broker01.web.qa.ext.phx1.redhat.com:5671',
        'amqps://messaging-devops-broker02.web.qa.ext.phx1.redhat.com:5671'
    ],
    'stage': [
        'amqps://messaging-devops-broker01.web.stage.ext.phx2.redhat.com:5671',
        'amqps://messaging-devops-broker02.web.stage.ext.phx2.redhat.com:5671'
    ],
    'prod': [
        'amqps://messaging-devops-broker01.web.prod.ext.phx2.redhat.com:5671',
        'amqps://messaging-devops-broker02.web.prod.ext.phx2.redhat.com:5671'
    ]
}
