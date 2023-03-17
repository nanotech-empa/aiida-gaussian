"""Tests for the :class:`aiida_gaussian.parsers.gaussian.GaussianBaseParser` class."""
# pylint: disable=redefined-outer-name
import pytest
from aiida.orm import Dict


def recursive_array_to_list(data):
    import numpy as np

    if isinstance(data, dict):
        return {key: recursive_array_to_list(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [recursive_array_to_list(value) for value in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data


@pytest.fixture
def inputs():
    return {
        "parameters": Dict(
            {
                "link0_parameters": {
                    "%chk": "aiida.chk",
                    "%nprocshared": "1",
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
        )
    }


def test_nan_inf(generate_calc_job_node, generate_parser, inputs, data_regression):
    """Test parsing a case where the parsed dictionary contains ``nan`` and ``inf`` values."""
    node = generate_calc_job_node("gaussian", "base", "nan_inf", inputs=inputs)
    parser = generate_parser("gaussian.base")
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    output_parameters = results["output_parameters"].get_dict()
    output_parameters.pop("coreelectrons")
    data = recursive_array_to_list(output_parameters)
    data_regression.check(data)

    # Check that the ``output_parameters`` content is serializable and can be stored
    results["output_parameters"].store()
