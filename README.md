[![build](https://github.com/nanotech-empa/aiida-gaussian/workflows/build/badge.svg)](https://github.com/nanotech-empa/aiida-gaussian/actions)
[![Coverage Status](https://coveralls.io/repos/github/nanotech-empa/aiida-gaussian/badge.svg?branch=master)](https://coveralls.io/github/nanotech-empa/aiida-gaussian?branch=master)
[![PyPI version](https://badge.fury.io/py/aiida-gaussian.svg)](https://badge.fury.io/py/aiida-gaussian)
[![DOI](https://zenodo.org/badge/241384761.svg)](https://zenodo.org/badge/latestdoi/241384761)

# aiida-gaussian

AiiDA plugin for the Gaussian quantum chemistry software

## Features

Gaussian input can be provided as a python dictionary following the convention defined by [pymatgen](https://pymatgen.org/)
```python
parameters = {
    'functional':'PBE1PBE',
    'basis_set':'6-31g',
    'charge': 0,
    'multiplicity': 1,
    'link0_parameters': {
        '%chk':'aiida.chk',
        '%mem':"1024MB",
        '%nprocshared': 4,
    },
    'route_parameters': {
        'scf': {
            'maxcycle': 128,
            'cdiis': None,
        },
        'nosymm': None,
        'output':'wfx',
        'opt': 'tight',
    },
    'input_parameters': { # appended at the end of the input
        'output.wfx':None
    }, 
}
```
In `route_parameters`, specifying `key: None` adds only `key` without the equals sign to the input script.

Parsing of the results is performed with the [cclib](https://github.com/cclib/cclib) library and by default all of its output is stored in the `output_parameters` node.

Additionally, simple plugins to submit the Gaussian utilities `formchk` and `cubegen` are provided.

## Installation

```shell
pip install aiida-gaussian
```

This installs the plugins to the AiiDA instance (to double-check, one can list all installed plugins by `verdi plugin list aiida.calculations`). After this, the Gaussian codes should be set up using the plugins (https://aiida.readthedocs.io/projects/aiida-core/en/latest/).

## Usage

A quick demo of how to submit a calculation:
```shell
verdi daemon start # make sure the daemon is running
cd examples
# Submit test calculation (argument is the label of gaussian code)
verdi run example_01_opt.py gaussian09 
```

## For maintainers

To create a new release, clone the repository, install development dependencies with `pip install '.[dev]'`, and then execute `bumpver update --major/--minor/--patch`.
This will:

  1. Create a tagged release with bumped version and push it to the repository.
  2. Trigger a GitHub actions workflow that creates a GitHub release.

Additional notes:

  - Use the `--dry` option to preview the release change.
  - The release tag (e.g. a/b/rc) is determined from the last release.
    Use the `--tag` option to switch the release tag.
