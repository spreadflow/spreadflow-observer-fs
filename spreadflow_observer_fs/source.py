from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from spreadflow_core.client import SchedulerClient

class FilesystemObserverSource(SchedulerClient):

    def __init__(self, query, directory):
        self.endpoint = 'spreadflow-observer-fs:' + ':'.join([directory, query])
        self.portmap = {'default': self}

    def __call__(self, item, send):
        send(item, self)
