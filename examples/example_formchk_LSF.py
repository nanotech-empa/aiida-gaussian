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
from aiida.orm import Code, Dict, SinglefileData, StructureData, load_node
from aiida.common import NotExistent, InputValidationError
from aiida.plugins import CalculationFactory

FormchkCalculation = CalculationFactory('gaussian.formchk')


def example(code):
    """Run simple DFT calculation"""

    gaussian_remotedata = load_node(164).outputs.remote_folder

    # Construct process builder

    builder = FormchkCalculation.get_builder()

    builder.gaussian_folder = gaussian_remotedata
    builder.code = code

    builder.metadata.options.resources = {
        "tot_num_mpiprocs": 1,
        "num_machines": 1,
    }


    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

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
    example(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
