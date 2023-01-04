"""pytest fixtures for simplified testing."""
from __future__ import absolute_import

import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']


@pytest.fixture
def fixture_localhost(aiida_localhost):
    """Return a localhost `Computer`."""
    localhost = aiida_localhost
    localhost.set_default_mpiprocs_per_machine(1)
    return localhost


@pytest.fixture
def fixture_code(fixture_localhost):
    """Return a `Code` instance configured to run calculations of given entry point on localhost `Computer`."""

    def _fixture_code(entry_point_name):
        from aiida.orm import Code
        return Code(
            input_plugin_name=entry_point_name,
            remote_computer_exec=[fixture_localhost, '/bin/true']
        )

    return _fixture_code


@pytest.fixture(scope='function')
def gaussian_code(aiida_local_code_factory):
    """Get a gaussian code.
    """
    gaussian_code = aiida_local_code_factory(executable='g09', entry_point='gaussian')
    return gaussian_code
