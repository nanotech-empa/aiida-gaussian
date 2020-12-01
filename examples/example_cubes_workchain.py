# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""
Run the Gaussian cubes workchain
"""

from __future__ import print_function
from __future__ import absolute_import

import ase.io
import numpy as np
import sys
import click

import matplotlib.pyplot as plt

from aiida.engine import run, run_get_node
from aiida.orm import Code, Dict, load_node, Bool, StructureData
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory, WorkflowFactory

GaussianCalculation = CalculationFactory('gaussian')
GaussianCubesWorkChain = WorkflowFactory('gaussian.cubes')


def example(gaussian_code, formchk_code, cubegen_code):

    # geometry
    ase_geom = ase.io.read("./p-quinodimethane.xyz")
    ase_geom.cell = np.diag([10.0, 10.0, 10.0])
    struct_node = StructureData(ase=ase_geom)

    # Run Gaussian calculation
    num_cores = 2
    memory_mb = 500

    builder = GaussianCalculation.get_builder()
    builder.code = gaussian_code
    builder.structure = struct_node
    builder.parameters = Dict(
        dict={
            'link0_parameters': {
                '%chk': 'aiida.chk',
                '%mem': "%dMB" % memory_mb,
                '%nprocshared': str(num_cores),
            },
            'functional': 'UB3LYP',
            'basis_set': '6-31g',
            'charge': 0,
            'multiplicity': 1,
            'route_parameters': {
                'scf': {
                    'cdiis': None,
                },
                'guess': 'mix',
                'nosymm': None,
                'sp': None,
            },
        })
    builder.metadata.options.resources = {
        "tot_num_mpiprocs": num_cores,
        "num_machines": 1,
    }
    # Should ask for extra ~1.5GB for libraries etc
    builder.metadata.options.max_memory_kb = memory_mb * 1024 + 1536 * 1024
    builder.metadata.options.max_wallclock_seconds = 5 * 60

    res, calc_node = run_get_node(builder)

    # Run cubes workchain

    wc_res, wc_node = run_get_node(
        GaussianCubesWorkChain,
        formchk_code=formchk_code,
        cubegen_code=cubegen_code,
        gaussian_calc_folder=calc_node.outputs.remote_folder,
        gaussian_output_params=res['output_parameters'],
        n_occ=Int(1),
        n_virt=Int(1),
        dx=Float(0.2),
        edge_space=Float(2.5),
    )

    # Plot cubes
    for outp in sorted(list(wc_node.outputs), reverse=True):
        if outp.startswith("cube_"):
            filename = "./%s.png" % outp
            arr = wc_node.outputs[outp].get_array('z_h2').T
            amax = np.max(np.abs(arr))
            plt.imshow(arr, vmin=-amax, vmax=amax, cmap='seismic')
            plt.axis('off')
            plt.savefig(filename, dpi=200, bbox_inches='tight')
            plt.close()
            print("Saved %s!" % filename)


@click.command('cli')
@click.argument('gaussian_codelabel')
@click.argument('formchk_codelabel')
@click.argument('cubegen_codelabel')
def cli(gaussian_codelabel, formchk_codelabel, cubegen_codelabel):
    """Click interface"""
    codes = []
    for codelabel in [
            gaussian_codelabel, formchk_codelabel, cubegen_codelabel
    ]:
        try:
            codes.append(Code.get_from_string(codelabel))
        except NotExistent:
            print("The code '{}' does not exist".format(codelabel))
            sys.exit(1)

    example(codes[0], codes[1], codes[2])


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
