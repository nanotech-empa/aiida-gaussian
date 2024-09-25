# pylint: disable=invalid-name
"""Run simple DFT calculation"""


import sys

import ase.io
import click
from aiida import orm
from aiida.common import NotExistent
from aiida.engine import run_get_node
from aiida.plugins import CalculationFactory

GaussianCalculation = CalculationFactory("gaussian")


def example_nmr_nics(gaussian_code):
    """Run an NMR calculation.

    The geometry also includes fake/ghost atoms (X),
    where nucleus-independent chemical shift (NICS) is calculated.
    """

    # structure
    structure = orm.StructureData(ase=ase.io.read("./naphthalene_nics.xyz"))

    num_cores = 1
    memory_mb = 300

    parameters = orm.Dict(
        {
            "link0_parameters": {
                "%chk": "aiida.chk",
                "%mem": "%dMB" % memory_mb,
                "%nprocshared": num_cores,
            },
            "functional": "BLYP",
            "basis_set": "6-31g",
            "charge": 0,
            "multiplicity": 1,
            "dieze_tag": "#P",
            "route_parameters": {
                "nmr": None,
            },
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

    # The advanced parser handles the NMR output
    builder.metadata.options.parser_name = "gaussian.advanced"

    # Should ask for extra +25% extra memory
    builder.metadata.options.max_memory_kb = int(1.25 * memory_mb) * 1024
    builder.metadata.options.max_wallclock_seconds = 5 * 60

    print("Running calculation...")
    res, _node = run_get_node(builder)

    print("NMR tensors of each atom:")
    for i, site in enumerate(structure.sites):
        print(site)
        print("  ", res["output_parameters"]["nmr_tensors"][i])


@click.command("cli")
@click.argument("codelabel", default="gaussian@localhost")
def cli(codelabel):
    """Click interface"""
    try:
        code = orm.load_code(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist")
        sys.exit(1)
    example_nmr_nics(code)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
