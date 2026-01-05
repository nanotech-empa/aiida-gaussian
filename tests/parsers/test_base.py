"""
Tests for the :class:`aiida_gaussian.parsers.gaussian.GaussianBaseParser` class.

Note on updated parsers (e.g. in Pymatgen) and data_regression:
If newer versions of parsers add extra fields, just update the reference data with
    pytest --force-regen
Although this will cause tests to fails with folder versions of the parser, but in
general it should not be a problem.
"""

# pylint: disable=redefined-outer-name


def recursive_array_to_list(data):
    """Recursively convert all numpy arrays in the mapping ``data`` to normal lists."""
    import numpy as np

    if isinstance(data, dict):
        return {key: recursive_array_to_list(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [recursive_array_to_list(value) for value in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data


def test_nan_inf(generate_calc_job_node, generate_parser, data_regression):
    """Test parsing a case where the parsed dictionary contains ``nan`` and ``inf`` values."""
    node = generate_calc_job_node("gaussian", "base", "nan_inf")
    parser = generate_parser("gaussian.base")
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    output_parameters = results["output_parameters"].get_dict()

    # Remove the ``coreelectrons`` key since it is not the target of this test and contains many zeros that would
    # significantly and unnecessarily increase the reference file in size.
    output_parameters.pop("coreelectrons")
    data = recursive_array_to_list(output_parameters)
    data_regression.check(data)

    # Check that the ``output_parameters`` content is serializable and can be stored
    results["output_parameters"].store()
