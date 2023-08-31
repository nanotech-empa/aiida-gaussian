"""Tests for gaussian plugin."""
import os
import textwrap

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


def test_parameters_gen_basis(fixture_code, generate_calc_job, file_regression):
    """Test that the ``basis_set`` parameter is respected even if ``gen_basis`` is set."""
    structure = StructureData(
        pymatgen_molecule=Molecule.from_file(
            os.path.join(tests.TEST_DIR, "data", "PtH.xyz")
        )
    )
    inputs = {
        "code": fixture_code("gaussian"),
        "structure": structure,
        "parameters": Dict(
            {
                "functional": "BLYP",
                "basis_set": "GenEcp",
                "gen_basis": textwrap.dedent(
                    """
                    H     0
                    S    3   1.00
                         13.0107010              0.19682158D-01
                          1.9622572              0.13796524
                          0.44453796             0.47831935
                    S    1   1.00
                          0.12194962             1.0000000
                    P    1   1.00
                          0.8000000              1.0000000
                    P    1   1.00
                          0.11704099050          1.0000000
                    ****
                    Pt     0
                    S    2   1.00
                         16.559563000           -0.53808800717
                         13.892440000            0.91402161377
                    S    1   1.00
                          5.8531044732           1.0000000
                    S    1   1.00
                          1.2498640609           1.0000000
                    S    1   1.00
                          0.55606439459          1.0000000
                    S    1   1.00
                          0.13793093812          1.0000000
                    S    1   1.00
                          0.48989034059D-01      1.0000000
                    P    4   1.00
                          8.1000000000           0.72955608128
                          7.2000000000          -0.95441807252
                          1.5588402917           0.57140490320
                          0.73230402180          0.49508234268
                    P    1   1.00
                          0.30270484669          1.0000000
                    P    1   1.00
                          0.12300000000          1.0000000
                    P    1   1.00
                          0.50000000000D-01      1.0000000
                    D    4   1.00
                          4.6299536825          -0.87774450596D-01
                          2.1980241252           0.21158360681
                          0.93629991261          0.46533857641
                          0.37160028160          0.41129165525
                    D    1   1.00
                          0.13155928617          1.0000000
                    F    1   1.00
                          0.6681300              1.0000000
                    ****

                    PT     0
                    PT-ECP     3     60
                    f potential
                      1
                    2      3.30956857            24.31437573
                    s-f potential
                      3
                    2     13.42865130           579.22386092
                    2      6.71432560            29.66949062
                    2      3.30956857           -24.31437573
                    p-f potential
                      3
                    2     10.36594420           280.86077422
                    2      5.18297210            26.74538204
                    2      3.30956857           -24.31437573
                    d-f potential
                      3
                    2      7.60047949           120.39644429
                    2      3.80023974            15.81092058
                    2      3.30956857           -24.31437573
                """
                ),
            }
        ),
        "metadata": {
            "options": {
                "resources": {
                    "num_machines": 1,
                    "tot_num_mpiprocs": 1,
                }
            }
        },
    }
    tmp_path, _ = generate_calc_job(GaussianCalculation, inputs)
    content_input_file = (tmp_path / GaussianCalculation.INPUT_FILE).read_text()
    file_regression.check(content_input_file, encoding="utf-8", extension=".in")
