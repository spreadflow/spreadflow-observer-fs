from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from spreadflow_core.remote import MessageHandler, SchedulerClientFactory, \
    SchedulerProtocol, ClientEndpointMixin, StrportGeneratorMixin
from spreadflow_format_bson import MessageParser

class FilesystemObserverSource(ClientEndpointMixin, StrportGeneratorMixin):

    def __init__(self, query, directory, **kwds):
        self.strport = self.strport_generate('spreadflow-observer-fs',
                                             directory, query, **kwds)

    def get_client_protocol_factory(self, scheduler, reactor):
        handler = MessageHandler(scheduler, {'default': self})
        return SchedulerClientFactory.forProtocol(
            SchedulerProtocol, handler=handler, parser_factory=MessageParser)

    def __call__(self, item, send):
        send(item, self)
