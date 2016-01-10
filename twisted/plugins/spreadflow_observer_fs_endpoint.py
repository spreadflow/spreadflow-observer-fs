import ast
import os
from spreadflow_observer_fs.compat import fsencode
from twisted.internet.endpoints import ProcessEndpoint
from twisted.internet.interfaces import IStreamClientEndpointStringParserWithReactor
from twisted.plugin import IPlugin
from twisted.python.procutils import which
from zope.interface import implementer


@implementer(IPlugin, IStreamClientEndpointStringParserWithReactor)
class SpreadflowObserverFSProcessEndpoint(object):
    prefix = 'spreadflow-observer-fs'

    def _binary_name(self, type):
        if not type:
            try:
                import PyObjCTools
                type = 'spotlight'
            except ImportError:
                type = 'default'

        return "spreadflow-observer-fs-%s" % type


    def _find_executable(self, type):
        binary_name = self._binary_name(type)
        executable = which(binary_name)

        if not executable:
            # walk up the directory hierarchy and try to find the path to a
            # helper tool built with buildout.
            executable = os.path.abspath(__file__)
            while os.path.dirname(executable) != executable:
                candidate = os.path.join(executable, 'bin', binary_name)
                if os.path.exists(candidate):
                    executable = candidate
                    break
                executable = os.path.dirname(executable)
        else:
            executable = None

        return executable


    def _parse(self, reactor, directory, query, native_query=True, type=None, executable=None):

        if not executable:
            executable = self._find_executable(type)

        args = (executable,)
        if ast.literal_eval(str(native_query)):
            args += ('-n',)
        args += (directory, query)

        return ProcessEndpoint(reactor, executable, args=map(fsencode, args))


    def parseStreamClient(self, reactor, *args, **kwargs):
        return self._parse(reactor, *args, **kwargs)


spreafllow_observer_fs_endpoint = SpreadflowObserverFSProcessEndpoint()
