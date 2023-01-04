# pylint: disable=invalid-name
"""Run simple DFT calculation"""


import sys

import click
import pymatgen as mg
from aiida.common import NotExistent
from aiida.engine import submit
from aiida.orm import Code, Dict, StructureData
from aiida.plugins import CalculationFactory

GaussianCalculation = CalculationFactory("gaussian")


def example_dft(gaussian_code):
    """Run simple DFT calculation"""

    print("Testing Gaussian Input Creation")

    # structure
    structure = StructureData(pymatgen_molecule=mg.Molecule.from_file("./ch4.xyz"))

    num_cores = 2
    memory_mb = 300

    # parameters
    parameters = Dict(
        {
            "link0_parameters": {
                "%chk": "aiida.chk",
                "%mem": "%dMB" % memory_mb,
                "%nprocshared": num_cores,
            },
            "functional": "PBE1PBE",
            "basis_set": "6-31g",
            "route_parameters": {"nosymm": None, "Output": "WFX"},
            "input_parameters": {"output.wfx": None},
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
    builder.metadata.options.max_wallclock_seconds = 3 * 60

    builder.metadata.dry_run = True
    builder.metadata.store_provenance = False

    process_node = submit(builder)

    print("Submitted dry_run in" + str(process_node.dry_run_info))


@click.command("cli")
@click.argument("codelabel")
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
