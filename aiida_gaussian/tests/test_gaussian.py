""" Tests for gaussian plugin

"""
from __future__ import print_function
from __future__ import absolute_import

from aiida.engine import run
from aiida.orm import Code, Dict, StructureData
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

from pymatgen.core import Molecule

import os
from aiida_gaussian import tests


def test_gaussian(fixture_code):

    geometry_file = os.path.join(tests.TEST_DIR, "data", 'ch4.xyz')
    expected_inp_file = os.path.join(tests.TEST_DIR, "data", 'gaussian_test.inp')

    # structure
    structure = StructureData(pymatgen_molecule=Molecule.from_file(geometry_file))

    num_cores = 1
    memory_mb = 1000

    # Main parameters: geometry optimization
    parameters = {
        'link0_parameters': {
            '%chk': 'aiida.chk',
            '%mem': "%dMB" % memory_mb,
            '%nprocshared': str(num_cores),
        },
        'functional': 'BLYP',
        'basis_set': '6-31g',
        'charge': 0,
        'multiplicity': 1,
        'route_parameters': {
            'scf': {
                'maxcycle': 512,
                'cdiis': None
            },
            'nosymm': None,
            'opt': None,
        },
    }

    # Build the inputs dictionary with a "fake" executable

    inputs = {
        'code': fixture_code('gaussian'),  #load_code("gaussian09@localhost"),
        'structure': structure,
        'parameters': Dict(parameters),
        'metadata': {
            'options': {
                'resources': {
                    'num_machines': 1,
                    'tot_num_mpiprocs': 1,
                },
                'max_wallclock_seconds': 1800,
                'withmpi': False
            }
        }
    }

    # Prepare the fake calculation for submission in a "sandbox folder"

    from aiida.engine.utils import instantiate_process
    from aiida.manage.manager import get_manager
    from aiida.common.folders import SandboxFolder

    manager = get_manager()
    runner = manager.get_runner()

    process_class = CalculationFactory('gaussian')
    process = instantiate_process(runner, process_class, **inputs)

    sandbox_folder = SandboxFolder()

    calc_info = process.prepare_for_submission(sandbox_folder)

    with sandbox_folder.open('aiida.inp') as handle:
        input_written = handle.read()

    with open(expected_inp_file, 'r') as f:
        expected_inp = f.read()

    assert (input_written == expected_inp)
