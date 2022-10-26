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
from aiida.plugins import WorkflowFactory

import pymatgen as mg

GaussianBaseWorkChain = WorkflowFactory('gaussian.base')


def example_dft(gaussian_code):
    """Run a simple gaussian optimization"""

    # structure
    structure = StructureData(pymatgen_molecule=mg.Molecule.from_file('./ch4.xyz'))

    num_cores = 4
    memory_mb = 40000

    # Main parameters: geometry optimization
    parameters = Dict(
        dict={
            'link0_parameters': {
                '%chk': 'aiida.chk',
                '%mem': "%dMB" % memory_mb,
                '%nprocshared': num_cores,
            },
            'functional': 'uB3LYP',
            'basis_set': '6-31g',
            'charge': -1,
            'multiplicity': 2,
            'route_parameters': {
                'scf': {
                    'conver': 7,
                    'maxcycle': 140,
                },
                'sp': None,
            },
        }
    )

    # Construct process builder

    builder = GaussianBaseWorkChain.get_builder()

    builder.gaussian.structure = structure
    builder.gaussian.parameters = parameters
    builder.gaussian.code = gaussian_code

    builder.gaussian.metadata.options.resources = {
        "num_machines": 1,
        "tot_num_mpiprocs": num_cores,
    }

    # Should ask for extra +25% extra memory
    builder.gaussian.metadata.options.max_memory_kb = int(1.25 * memory_mb) * 1024
    builder.gaussian.metadata.options.max_wallclock_seconds = 5 * 60

    print("Running calculation...")
    res, _node = run_get_node(builder)

    print("Final scf energy: %.4f" % res['output_parameters']['scfenergies'][-1])


@click.command('cli')
@click.argument('codelabel', default='gaussian@localhost')
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist")
        sys.exit(1)
    example_dft(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter