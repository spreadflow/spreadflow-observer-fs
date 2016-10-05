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
import shutil
import subprocess
import threading
import time
import unittest

from bson import BSON

try:
    import queue
except ImportError:
    import Queue as queue

MAXWAIT = 5.0
FIXTURE_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

class _TimeoutError(Exception):
    pass

class _StreamReader(object):
    """
    A non-blocking reader for multiple input streams.
    """
    def __init__(self, streams):
        self._queue = queue.Queue()
        self._streams = streams
        self._threads = None

    def drain(self, timeout=MAXWAIT):
        if timeout > 0:
            deadline = time.time() + timeout

        while True:
            if timeout > 0 and time.time() > deadline:
                raise _TimeoutError()

            try:
                stream, data = self._queue.get(timeout=timeout)
            except queue.Empty:
                break
            else:
                yield stream, data

    def start(self):
        for stream in self._streams:
            thread = threading.Thread(target=self._reader, args=[stream])
            thread.daemon = True
            thread.start()

    def join(self):
        if self._threads is not None:
            for thread in self._threads:
                thread.join()

    def _reader(self, stream):
        """
        Performs non-blocking read from a stream. Use it in a thread.
        """
        flags = fcntl.fcntl(stream, fcntl.F_GETFL)
        fcntl.fcntl(stream, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while True:
            try:
                data = stream.read()
            except (OSError, IOError) as e:
                if e.errno == errno.EINTR or e.errno == errno.EAGAIN:
                    continue
                raise
            else:
                if data is not None:
                    self._queue.put((stream, data))
                    if data == b'':
                        break

class SpreadflowObserverIntegrationTestCase(unittest.TestCase):
    """
    Integration tests for spreadflow filesystem observer process.
    """

    longMessage = True

    def _format_stream(self, stdout, stderr):
        return '\nSTDOUT:\n{0}\nSTDERR:\n{1}'.format(
            stdout or '*** EMPTY ***', stderr or '*** EMPTY ***')

    def test_subprocess_worker_producer(self):
        """
        Worker process reads messages from stdin and writes results to stdout.
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

            reader = _StreamReader([proc.stdout, proc.stderr])
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

            # Close stdin, this signals the observer process to terminate.
            proc.stdin.close()

            proc.wait()
            self.assertEqual(proc.returncode, 0, self._format_stream('*** BINARY ***', stream_data[proc.stderr]))

            for stream, data in reader.drain(0):
                stream_data[stream] += data

            reader.join()

            # Verify output.
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

            key = item['inserts'][0]
            self.assertIn(key, item['data'])

            self.assertEqual(item['data'][key]['path'], txtpath)
