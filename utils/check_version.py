"""Check that version numbers match.

Check version number in setup.json and aiida_gaussian/__init__.py and make sure
they match.
"""
from __future__ import absolute_import
from __future__ import print_function
import os
import json
import sys

this_path = os.path.split(os.path.realpath(__file__))[0]

# Get content of setup.json
setup_fname = 'setup.json'
setup_path = os.path.join(this_path, os.pardir, setup_fname)
with open(setup_path) as f:
    setup_content = json.load(f)

# Get version from python package
sys.path.insert(0, os.path.join(this_path, os.pardir))
import aiida_gaussian  # pylint: disable=wrong-import-position
version = aiida_gaussian.__version__

if version != setup_content['version']:
    print("Version number mismatch detected:")
    print("Version number in '{}': {}".format(setup_fname, setup_content['version']))
    print("Version number in '{}/__init__.py': {}".format('aiida_gaussian', version))
    sys.exit(1)

# Overwrite version in setup.json
#setup_content['version'] = version
#with open(setup_path, 'w') as f:
#	json.dump(setup_content, f, indent=4, sort_keys=True)
