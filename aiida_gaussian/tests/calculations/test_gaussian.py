"""Tests for gaussian plugin."""
import os

from aiida.orm import Dict, StructureData
from pymatgen.core import Molecule

from aiida_gaussian import tests
from aiida_gaussian.calculations.gaussian import GaussianCalculation


def test_default(fixture_code, generate_calc_job, file_regression):
    """Test a default calculation for :class:`aiida_gaussian.calculations.gaussian.GaussianCalculation`."""
    geometry_file = os.path.join(tests.TEST_DIR, "data", "ch4.xyz")

    structure = StructureData(pymatgen_molecule=Molecule.from_file(geometry_file))

    num_cores = 1
    memory_mb = 1000

    # Main parameters: geometry optimization
    parameters = {
        "link0_parameters": {
            "%chk": "aiida.chk",
            "%mem": "%dMB" % memory_mb,
            "%nprocshared": str(num_cores),
        },
        "functional": "BLYP",
        "basis_set": "6-31g",
        "charge": 0,
        "multiplicity": 1,
        "route_parameters": {
            "scf": {"maxcycle": 512, "cdiis": None},
            "nosymm": None,
            "opt": None,
        },
    }

    # Build the inputs dictionary with a "fake" executable

    inputs = {
        "code": fixture_code("gaussian"),  # load_code("gaussian09@localhost"),
        "structure": structure,
        "parameters": Dict(parameters),
        "metadata": {
            "options": {
                "resources": {
                    "num_machines": 1,
                    "tot_num_mpiprocs": 1,
                },
                "max_wallclock_seconds": 1800,
                "withmpi": False,
            }
        },
    }

    tmp_path, _ = generate_calc_job(GaussianCalculation, inputs)
    content_input_file = (tmp_path / GaussianCalculation.INPUT_FILE).read_text()
    file_regression.check(content_input_file, encoding="utf-8", extension=".in")
