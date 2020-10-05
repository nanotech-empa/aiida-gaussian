# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
Run the Gaussian cubegen utility on the specified formchk output
"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.engine import run
from aiida.orm import Code, Dict, SinglefileData, StructureData, load_node, Bool
from aiida.common import NotExistent, InputValidationError
from aiida.plugins import CalculationFactory

CubegenCalculation = CalculationFactory('gaussian.cubegen')


def example(code, formchk_pk):

    builder = CubegenCalculation.get_builder()
    builder.parent_calc_folder = load_node(formchk_pk).outputs.remote_folder
    builder.code = code

    builder.parameters = Dict(
        dict={
            "homo": {
                "kind": "MO=Homo",
                "npts": -2,
            },
            "density": {
                "kind": "Density=SCF",
                "npts": -2,
            },
        })

    builder.retrieve_cubes = Bool(True)

    builder.metadata.options.resources = {
        "tot_num_mpiprocs": 1,
        "num_machines": 1,
    }

    builder.metadata.options.max_wallclock_seconds = 5 * 60

    print("Submitted calculation...")
    run(builder)


@click.command('cli')
@click.argument('codelabel')
@click.argument('formchk_pk')
def cli(codelabel, formchk_pk):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example(code, formchk_pk)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
