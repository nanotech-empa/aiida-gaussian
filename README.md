[![build](https://github.com/nanotech-empa/aiida-gaussian/workflows/build/badge.svg)](https://github.com/nanotech-empa/aiida-gaussian/actions)
[![Coverage Status](https://coveralls.io/repos/github/nanotech-empa/aiida-gaussian/badge.svg?branch=master)](https://coveralls.io/github/nanotech-empa/aiida-gaussian?branch=master)
[![PyPI version](https://badge.fury.io/py/aiida-gaussian.svg)](https://badge.fury.io/py/aiida-gaussian)

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

Multiple `link1` sections are allowed through the `extra_link1_sections` parameter but this is discouraged and steps should be separated into AiiDA workflow steps.

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
verdi run example_01_opt_and_triplet.py gaussian09 
```

