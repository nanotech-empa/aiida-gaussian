# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Run simple DFT calculation"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.engine import run, run_get_node
from aiida.orm import Code, Dict, StructureData
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

import pymatgen as mg

GaussianCalculation = CalculationFactory('gaussian')


def example_dft(gaussian_code):
    """Run a simple gaussian optimization"""

    # structure
    structure = StructureData(pymatgen_molecule=mg.Molecule.from_file('./ch4.xyz'))

    num_cores = 1
    memory_mb = 300

    # Main parameters: geometry optimization
    parameters = Dict(
        dict={
            'link0_parameters': {
                '%chk': 'aiida.chk',
                '%mem': "%dMB" % memory_mb,
                '%nprocshared': num_cores,
            },
            'functional': 'BLYP',
            'basis_set': '6-31g',
            'charge': 0,
            'multiplicity': 1,
            'route_parameters': {
                'scf': {
                    'cdiis': None,
                },
                'nosymm': None,
                'opt': None,
            },
        }
    )

    # Construct process builder

    builder = GaussianCalculation.get_builder()

    builder.structure = structure
    builder.parameters = parameters
    builder.code = gaussian_code

    builder.metadata.options.resources = {
        "num_machines": 1,
        "tot_num_mpiprocs": num_cores,
    }

    # Should ask for extra +25% extra memory
    builder.metadata.options.max_memory_kb = int(1.25 * memory_mb) * 1024
    builder.metadata.options.max_wallclock_seconds = 5 * 60

    print("Running calculation...")
    res, _node = run_get_node(builder)

    print("Final scf energy: %.4f" % res['output_parameters']['scfenergies'][-1])


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example_dft(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
