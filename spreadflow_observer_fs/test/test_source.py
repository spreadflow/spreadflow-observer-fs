# -*- coding: utf-8 -*-
# pylint: disable=too-many-public-methods

"""
Integration tests for spreadflow filesystem observer source.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy

from bson import BSON
from datetime import datetime
from twisted.internet import defer

from mock import Mock
from testtools import TestCase, run_test_with
from testtools.twistedsupport import AsynchronousDeferredRunTest

from spreadflow_core.scheduler import Scheduler
from spreadflow_delta.test.matchers import MatchesSendDeltaItemInvocation

from spreadflow_observer_fs.source import FilesystemObserverSource


def _spawnProcess(processProtocol, executable, args=(), env={}, path=None, uid=None, gid=None, usePTY=0, childFDs=None):
    """
    Spawn process method signature.
    """

class SpreadflowSourceIntegrationTestCase(TestCase):
    """
    Integration tests for spreadflow filesystem observer source.
    """

    @run_test_with(AsynchronousDeferredRunTest)
    @defer.inlineCallbacks
    def test_source_process(self):
        source = FilesystemObserverSource('*.txt', '/some/directory')

        reactor = Mock()
        reactor.spawnProcess = Mock(spec=_spawnProcess)

        scheduler = Mock()
        scheduler.send = Mock(spec=Scheduler.send)

        # Attach source to the scheduler.
        yield source.attach(scheduler, reactor)
        self.assertEquals(reactor.spawnProcess.call_count, 1)

        # Simulate a message directed to the source.
        msg = {
            'port': 'default',
            'item': {
                'type': 'delta',
                'date': datetime(2010, 10, 20, 20, 10),
                'inserts': ['abcdefg'],
                'deletes': ['hiklmno'],
                'data': {
                    'abcdefg': {
                        'path': '/some/directory/xyz.txt'
                    }
                }
            }
        }

        matches = MatchesSendDeltaItemInvocation(copy.deepcopy(msg['item']), source)
        source.peer.dataReceived(BSON.encode(msg))
        self.assertEquals(scheduler.send.call_count, 1)
        self.assertThat(scheduler.send.call_args, matches)
