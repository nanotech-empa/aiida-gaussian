[![Build Status](https://travis-ci.org/nanotech-empa/aiida-gaussian.svg?branch=master)](https://travis-ci.org/nanotech-empa/aiida-gaussian)
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
Specifying `key: None` adds only the keyword without the equals sign.

Multiple `link1` sections are allowed through the `extra_link1_sections` parameter but this is discouraged and steps should be separated into AiiDA workflow steps.

Additionally, simple plugins to submit the Gaussian utilities `formchk` and `cubegen` are provided.

## Installation

```shell
pip install aiida-gaussian
```

## Usage

A quick demo of how to submit a calculation:
```shell
verdi daemon start         # make sure the daemon is running
cd examples
verdi run example.py        # submit test calculation
verdi process list -a  # check status of calculation
```

## License

MIT

## Contact

kristjaneimre@gmail.com

