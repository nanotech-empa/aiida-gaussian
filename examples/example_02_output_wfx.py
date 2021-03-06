# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Run simple DFT calculation"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.engine import run, submit
from aiida.orm import Code, Dict, StructureData
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

import pymatgen as mg

GaussianCalculation = CalculationFactory('gaussian')


def example_dft(gaussian_code):
    """Run simple DFT calculation"""

    print("Testing Gaussian Input Creation")

    # structure
    structure = StructureData(
        pymatgen_molecule=mg.Molecule.from_file('./ch4.xyz'))

    num_cores = 2
    memory_mb = 200

    # parameters
    parameters = Dict(
        dict={
            'link0_parameters': {
                '%chk': 'aiida.chk',
                '%mem': '%dMB' % memory_mb,
                '%nprocshared': num_cores,
            },
            'functional': 'PBE1PBE',
            'basis_set': '6-31g',
            'route_parameters': {
                'nosymm': None,
                'Output': 'WFX'
            },
            'input_parameters': {
                'output.wfx': None
            },
        })

    # Construct process builder

    builder = GaussianCalculation.get_builder()

    builder.structure = structure
    builder.parameters = parameters
    builder.code = gaussian_code

    builder.metadata.options.resources = {
        "num_machines": 1,
        "tot_num_mpiprocs": num_cores,
    }

    # Should ask for extra ~1.5GB for libraries etc
    builder.metadata.options.max_memory_kb = (memory_mb + 1536) * 1024

    builder.metadata.options.max_wallclock_seconds = 3 * 60

    builder.metadata.dry_run = True
    builder.metadata.store_provenance = False

    process_node = submit(builder)

    print("Submitted dry_run in" + str(process_node.dry_run_info))


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
