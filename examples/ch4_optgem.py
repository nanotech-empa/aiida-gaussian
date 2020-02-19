# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Run simple DFT calculation"""

from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import ase.build
import click

from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData, StructureData)
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

import pymatgen as mg

GaussianCalculation = CalculationFactory('gaussian')


def example_dft(g_code):
    """Run simple DFT calculation"""

    print("Testing Gaussian Input Creation")

    pwd = os.path.dirname(os.path.realpath(__file__))

    # structure
    structure = StructureData(pymatgen_molecule=mg.Molecule.from_file('./ch4.xyz'))

    # parameters
    parameters = Dict(
        dict={
            'functional':'PBE1PBE',
            'basis_set':'6-31g',
            'route_parameters':{
                'nosymm': None,
                'opt': None
                },
            # 'input_parameters':{'output.wfx':None},
            'link0_parameters':{
                '%chk':'mychk.chk',
                '%mem':'1gb',
                '%nprocshared':'2'
                },
        })

    # Construct process builder

    builder = GaussianCalculation.get_builder()

    builder.structure = structure
    builder.parameters = parameters
    builder.code = g_code

    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2,
        "tot_num_mpiprocs": parameters['link0_parameters']['%nprocshared']
    }
    # builder.metadata.options.max_memory_kb = int(parameters['link0_parameters']['%mem'][:-2])

    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60
    builder.metadata.dry_run = False
    builder.metadata.store_provenance = True

    print("Submitted calculation...")
    run(builder)


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
