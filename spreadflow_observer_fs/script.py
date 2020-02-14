from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

try:
    import queue
except ImportError:
    import Queue as queue
import argparse
import importlib
import os
import sys
import threading
from spreadflow_observer_fs.protocol import MessageFactory
from pathtools.patterns import match_path, filter_paths
from watchdog.events import PatternMatchingEventHandler


class EventHandler(PatternMatchingEventHandler):
    def __init__(self, pattern, changes_queue):
        super(EventHandler, self).__init__(patterns=[pattern],
                ignore_patterns=None, ignore_directories=True,
                case_sensitive=False)
        self._changes_queue = changes_queue
        self._inserts = []
        self._deletes = []

    def on_moved(self, event):
        if event.src_path and match_path(event.src_path,
                included_patterns=self.patterns,
                excluded_patterns=self.ignore_patterns,
                case_sensitive=self.case_sensitive):
            self._deletes.append(event.src_path)
        if event.dest_path and match_path(event.dest_path,
                included_patterns=self.patterns,
                excluded_patterns=self.ignore_patterns,
                case_sensitive=self.case_sensitive):
            self._inserts.append(event.dest_path)
        self.flush()

    def on_created(self, event):
        self._inserts.append(event.src_path)
        self.flush()

    def on_deleted(self, event):
        self._deletes.append(event.src_path)
        self.flush()

    def on_modified(self, event):
        self._deletes.append(event.src_path)
        self._inserts.append(event.src_path)
        self.flush()

    def flush(self):
        if len(self._inserts) or len(self._deletes):
            self._changes_queue.put((tuple(self._deletes), tuple(self._inserts)))

        self._inserts = []
        self._deletes = []


class WatchdogObserverCommand(object):

    query = None
    native_query = None
    directory = None
    observer_class = 'watchdog.observers.Observer'

    def __init__(self, out=None):
        if out is None:
            try:
                # Python 3 does not allow us to write binary data to stdout.
                # Except if we use the buffer directly :/
                # http://stackoverflow.com/a/908440/2779045
                self._out = sys.stdout.buffer #pylint: disable=no-member
            except AttributeError:
                self._out = sys.stdout

    def load_observer(self, fqcn):
        module_name, class_name = fqcn.rsplit(".", 1)
        observer_module = importlib.import_module(module_name)
        return getattr(observer_module, class_name)

    def run(self, args):

        parser = argparse.ArgumentParser(prog=args[0])
        parser.add_argument('directory', metavar='DIR',
                            help='Base directory')
        parser.add_argument('query', metavar='PATTERN',
                            help='Pattern or query string')
        parser.add_argument('-n', '--native-query', action='store_true',
                            help='PATTERN is a native query for the selected observer')
        parser.add_argument('-o', '--observer-class', metavar='CLASS',
                            help='Specify the watchdog observer implementation (fully qualified class name).')

        parser.parse_args(args[1:], namespace=self)

        try:
            Observer = self.load_observer(self.observer_class)
        except:
            parser.error("Watchdog observer implementation not found")

        changes_queue = queue.Queue()

        stop_sentinel = object()
        def stdin_watch():
            while sys.stdin.read():
                pass
            changes_queue.put(stop_sentinel)

        stdin_watch_thread = threading.Thread(target=stdin_watch)
        stdin_watch_thread.start()

        pattern = self.query
        if not self.native_query:
            pattern = '*/' + pattern

        event_handler = EventHandler(pattern, changes_queue)

        observer = Observer()
        observer.schedule(event_handler, self.directory, recursive=True)
        observer.start()

        factory = MessageFactory()

        for root, dirs, files in os.walk(os.path.abspath(self.directory)):
            paths = [os.path.join(root, f) for f in files]
            inserts = tuple(filter_paths(paths, included_patterns=[pattern], case_sensitive=False))
            if len(inserts):
                changes_queue.put((tuple(), tuple(inserts)))

        while True:
            try:
                item = changes_queue.get(timeout=1000)
                if item == stop_sentinel:
                    break

                (deletable_paths, insertable_paths) = item

                insertable_meta = []
                insertable_paths_ok = []
                for path in insertable_paths[:]:
                    try:
                        insertable_meta.append({'stat': tuple(os.stat(path))})
                        insertable_paths_ok.append(path)
                    except OSError:
                        continue

                for msg in factory.update(deletable_paths, tuple(insertable_paths_ok), tuple(insertable_meta)):
                    self._out.write(msg)
                    self._out.flush()

                changes_queue.task_done()
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break

        observer.stop()
        observer.join()
        stdin_watch_thread.join()

def main():
    cmd = WatchdogObserverCommand()
    sys.exit(cmd.run(sys.argv))
