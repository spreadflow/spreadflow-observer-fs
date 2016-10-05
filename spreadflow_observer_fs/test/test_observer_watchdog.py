# -*- coding: utf-8 -*-
# pylint: disable=too-many-public-methods

"""
Integration tests for spreadflow filesystem observer process.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import errno
import fcntl
import fixtures
import os
import subprocess
import threading
import time
import unittest

from bson import BSON
from spreadflow_core.test.util import StreamsReader


class SpreadflowObserverIntegrationTestCase(unittest.TestCase):
    """
    Integration tests for spreadflow filesystem observer process.
    """

    longMessage = True

    def _format_stream(self, stdout, stderr):
        return '\nSTDOUT:\n{0}\nSTDERR:\n{1}'.format(
            stdout or '*** EMPTY ***', stderr or '*** EMPTY ***')

    def test_observer_process(self):
        """
        Observer watches a directory for file changes and reports on stdout.
        """

        with fixtures.TempDir() as fix:

            rundir = fix.path
            pidfile = os.path.join(rundir, 'filesystem observer.pid')
            argv = [rundir, '*.txt']
            proc = subprocess.Popen(['spreadflow-observer-fs-default'] + argv,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)

            stream_data = {proc.stdout: b'', proc.stderr: b''}

            reader = StreamsReader([proc.stdout, proc.stderr])
            reader.start()

            # Write a file.
            tmppath = os.path.join(rundir, 'test.tmp')
            txtpath = os.path.join(rundir, 'test.txt')
            with open(tmppath, 'w') as stream:
                stream.write('5WpWC30X')
            os.rename(tmppath, txtpath)

            for stream, data in reader.drain():
                stream_data[stream] += data
                if stream_data[proc.stdout]:
                    break
            else:
                self.fail('Observer process is expected to emit a message to stdout{0}'.format(self._format_stream('*** BINARY ***', stream_data[proc.stderr])))

            # Verify output (create operation).
            msg = BSON(stream_data[proc.stdout]).decode()
            self.assertIn('item', msg)
            self.assertIn('port', msg)

            item = msg['item']
            self.assertEqual(msg['port'], 'default')

            self.assertIn('data', item)
            self.assertIn('inserts', item)
            self.assertIn('deletes', item)

            self.assertIsInstance(item['data'], collections.Mapping)
            self.assertIsInstance(item['inserts'], collections.Sequence)
            self.assertIsInstance(item['deletes'], collections.Sequence)

            self.assertEqual(len(item['data']), 1)
            self.assertEqual(len(item['inserts']), 1)
            self.assertEqual(len(item['deletes']), 0)

            origkey = item['inserts'][0]
            self.assertIn(origkey, item['data'])

            self.assertEqual(item['data'][origkey]['path'], txtpath)

            # Reset stdout buffer.
            stream_data[proc.stdout] = b''

            # Move a file.
            newpath = os.path.join(rundir, 'test-2.txt')
            os.rename(txtpath, newpath)

            for stream, data in reader.drain():
                stream_data[stream] += data
                if stream_data[proc.stdout]:
                    break
            else:
                self.fail('Observer process is expected to emit a message to stdout{0}'.format(self._format_stream('*** BINARY ***', stream_data[proc.stderr])))

            # Verify output (mv operation).
            msg = BSON(stream_data[proc.stdout]).decode()
            self.assertIn('item', msg)
            self.assertIn('port', msg)

            item = msg['item']
            self.assertEqual(msg['port'], 'default')

            self.assertIn('data', item)
            self.assertIn('inserts', item)
            self.assertIn('deletes', item)

            self.assertIsInstance(item['data'], collections.Mapping)
            self.assertIsInstance(item['inserts'], collections.Sequence)
            self.assertIsInstance(item['deletes'], collections.Sequence)

            # FIXME: Apparently there is a data-entry also for deletes. Figure
            # out whether this is really expected/necessary. Also compare to
            # the behavior of spreadflow-observer-fs-spotlight.
            self.assertEqual(len(item['data']), 2)
            self.assertEqual(len(item['inserts']), 1)
            self.assertEqual(len(item['deletes']), 1)

            oldkey = item['deletes'][0]
            newkey = item['inserts'][0]
            self.assertIn(newkey, item['data'])

            self.assertEqual(item['data'][newkey]['path'], newpath)
            self.assertEqual(origkey, oldkey)
            self.assertNotEqual(origkey, newkey)

            # Reset stdout buffer.
            stream_data[proc.stdout] = b''

            # Close stdin, this signals the observer process to terminate.
            proc.stdin.close()

            proc.wait()
            self.assertEqual(proc.returncode, 0, self._format_stream('*** BINARY ***', stream_data[proc.stderr]))

            for stream, data in reader.drain(0):
                stream_data[stream] += data

            reader.join()

