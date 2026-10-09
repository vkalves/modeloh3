"""Isolated H3 test nodes. Does not replace any production node registration."""
from . import base, v2

VERSION = 'h3-teste-mascara-v1'
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
for module in (base, v2):
    for name, cls in module.NODE_CLASS_MAPPINGS.items():
        key = 'H3T1_' + name
        NODE_CLASS_MAPPINGS[key] = cls
        NODE_DISPLAY_NAME_MAPPINGS[key] = '[TESTE V1] ' + module.NODE_DISPLAY_NAME_MAPPINGS.get(name, name)
