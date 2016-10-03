from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from spreadflow_core.remote import MessageHandler, SchedulerClientFactory, \
    SchedulerProtocol, ClientEndpointMixin
from spreadflow_format_bson import MessageParser

class FilesystemObserverSource(ClientEndpointMixin):

    def __init__(self, query, directory, **kwds):
        self.strport = 'spreadflow-observer-fs:' + ':'.join([directory, query])

        for key, value in kwds.items():
            self.strport += ':' + key + '=' + value

    def get_client_protocol_factory(self, scheduler, reactor):
        handler = MessageHandler(scheduler, {'default': self})
        return SchedulerClientFactory.forProtocol(
            SchedulerProtocol, handler=handler, parser_factory=MessageParser)

    def __call__(self, item, send):
        send(item, self)
