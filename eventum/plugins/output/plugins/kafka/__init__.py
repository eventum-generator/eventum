"""Package with kafka output plugin implementation."""

import os
import sysconfig

# On free-threaded Python, disable aiokafka C extensions to prevent
# the GIL from being re-enabled (extensions haven't declared GIL safety yet).
if sysconfig.get_config_var('Py_GIL_DISABLED'):
    os.environ.setdefault('AIOKAFKA_NO_EXTENSIONS', '1')
