# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
Runs the formchk utility on the specified gaussian calculation
"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.engine import run
from aiida.orm import Code, StructureData, load_node
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

FormchkCalculation = CalculationFactory('gaussian.formchk')


def example(code, gaussian_pk):

    gaussian_remotedata = load_node(gaussian_pk).outputs.remote_folder

    # Construct process builder

    builder = FormchkCalculation.get_builder()

    builder.parent_calc_folder = gaussian_remotedata
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
@click.argument('gaussian_pk')
def cli(codelabel, gaussian_pk):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example(code, gaussian_pk)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
