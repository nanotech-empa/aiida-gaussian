#!/usr/bin/env python
"""Check that version numbers match.
"""
import os
import json
import sys

this_path = os.path.split(os.path.realpath(__file__))[0]

# Get content of setup.json
setup_fname = 'setup.json'
setup_path = os.path.join(this_path, os.pardir, setup_fname)
with open(setup_path) as f:
    setup_content = json.load(f)
setup_version = setup_content['version']

# Get version from python package
sys.path.insert(0, os.path.join(this_path, os.pardir))
import aiida_gaussian  # pylint: disable=wrong-import-position,import-error
init_version = aiida_gaussian.__version__

github_version = None
if "TAG_VERSION" in os.environ:
    tag_v = os.environ['TAG_VERSION']
    github_version = tag_v.split("/")[-1].replace('v', '')

if setup_version != init_version or (
    github_version is not None and setup_version != github_version
):
    print("Version number mismatch detected:")
    print("Version number in {}: {}".format(setup_fname, setup_version))
    print("Version number in 'aiida_gaussian/__init__.py': {}".format(init_version))
    if github_version is not None:
        print("Version number in GitHub tag: {}".format(github_version))
    sys.exit(1)
