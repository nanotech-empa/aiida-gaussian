# pylint: disable=invalid-name
"""Run simple DFT calculation"""


import sys

import click
import pymatgen as mg
from aiida.common import NotExistent
from aiida.engine import run, run_get_node
from aiida.orm import Code, Dict, StructureData
from aiida.plugins import WorkflowFactory

GaussianBaseWorkChain = WorkflowFactory("gaussian.base")


def example_dft(gaussian_code):
    """Run a base restart workchain.

    The first run should except with ASyTop error, then the handler should
    restart the calculation with structure coordinates rounded to the 4th digit.
    """

    # structure
    structure = StructureData(pymatgen_molecule=mg.Molecule.from_file("./c2h6.xyz"))

    num_cores = 2
    memory_mb = 300

    # Main parameters: geometry optimization
    parameters = Dict(
        {
            "link0_parameters": {
                "%chk": "aiida.chk",
                "%mem": "%dMB" % memory_mb,
                "%nprocshared": num_cores,
            },
            "functional": "B3LYP",
            "basis_set": "6-31g",
            "charge": 0,
            "multiplicity": 1,
            "route_parameters": {
                "scf": {
                    "conver": 7,
                    "maxcycle": 140,
                },
                "sp": None,
            },
        }
    )

    # Construct process builder

    builder = GaussianBaseWorkChain.get_builder()

    # Handle the ASyTop error
    builder.handler_overrides = Dict({"handle_asytop_error": True})

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

    print("Final scf energy: %.4f" % res["output_parameters"]["scfenergies"][-1])


@click.command("cli")
@click.argument("codelabel", default="gaussian@localhost")
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist")
        sys.exit(1)
    example_dft(code)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
