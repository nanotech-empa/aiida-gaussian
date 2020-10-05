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
from aiida.common import NotExistent, InputValidationError
from aiida.plugins import CalculationFactory

import pymatgen as mg

GaussianCalculation = CalculationFactory('gaussian')


def example_dft(gaussian_code):
    """Run a simple two-step gaussian calculation"""

    # structure
    structure = StructureData(
        pymatgen_molecule=mg.Molecule.from_file('./ch4.xyz'))

    num_cores = 1
    memory_mb = 1000

    # Main parameters: geometry optimization
    parameters = Dict(
        dict={
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
        })

    # Link1 step: population analysis with better basis
    link1_parameters = Dict(
        dict={
            'link0_parameters': {
                '%chk': 'aiida.chk',
                '%mem': "%dMB" % memory_mb,
                '%nprocshared': str(num_cores),
            },
            'functional': 'BLYP',
            'basis_set': '6-311g',
            'charge': 0,
            'multiplicity': 1,
            'route_parameters': {
                'nosymm': None,
                'guess': 'read',
                'geom': 'checkpoint',
                'pop': 'Hirshfeld',
                'sp': None,
            }
        })

    # Construct process builder

    builder = GaussianCalculation.get_builder()

    builder.structure = structure
    builder.parameters = parameters
    builder.code = gaussian_code

    builder.extra_link1_sections = {
        "extra1": link1_parameters,
    }

    builder.metadata.options.resources = {
        "tot_num_mpiprocs": num_cores,
        "num_machines": 1,
    }

    builder.metadata.options.max_memory_kb = memory_mb * 1024

    builder.metadata.options.max_wallclock_seconds = 5 * 60

    #builder.metadata.options.custom_scheduler_commands = "#BSUB -R \"rusage[mem=%d,scratch=%d]\"" % (
    #    int(memory_mb/num_cores*1.25),
    #    int(memory_mb/num_cores*2.15*2)
    #)

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
