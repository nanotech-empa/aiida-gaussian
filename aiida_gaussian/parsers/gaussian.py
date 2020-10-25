# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import tempfile
import numpy as np

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict, StructureData

import pymatgen.io.gaussian as mgaus

import cclib
import re
import ase


class GaussianBaseParser(Parser):
    """Basic AiiDA parser for the output of Gaussian"""
    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        try:
            out_folder = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        fname = self.node.process_class.OUTPUT_FILE

        if fname not in out_folder._repository.list_object_names():
            return self.exit_codes.ERROR_OUTPUT_MISSING

        log_file_path = os.path.join(
            out_folder._repository._get_base_folder().abspath, fname)

        exit_code = self._parse_log(log_file_path)

        if exit_code is not None:
            return exit_code

        return ExitCode(0)

    def _parse_log(self, log_file_path):
        """CCLIB parsing"""

        data = cclib.io.ccread(log_file_path)

        property_dict = data.getattributes()

        # replace the first delta-energy of nan with zero
        # as nan is not allowed in AiiDA nodes
        if 'scfvalues' in property_dict:
            property_dict['scfvalues'] = [
                np.nan_to_num(svs) for svs in property_dict['scfvalues']
            ]

        self.out("output_parameters", Dict(dict=property_dict))

        # in case of geometry optimization,
        # return the last geometry as a separated node
        if "atomcoords" in property_dict:
            if len(property_dict["atomcoords"]) > 1:

                opt_coords = property_dict["atomcoords"][-1]

                # The StructureData output node needs a cell,
                # even though it is not used in gaussian.
                # Set it arbitrarily as double the bounding box + 10
                double_bbox = 2 * np.ptp(opt_coords, axis=0) + 10

                ase_opt = ase.Atoms(property_dict["atomnos"],
                                    positions=property_dict["atomcoords"][-1],
                                    cell=double_bbox)

                structure = StructureData(ase=ase_opt)
                self.out('output_structure', structure)

        # additional checks on the output file
        with open(log_file_path, 'r') as logf:
            log_file = logf.read()

        if "Convergence failure -- run terminated." in log_file:
            return self.exit_codes.ERROR_SCF_FAILURE

        # Any other error...
        if "Error termination" in log_file:
            return self.exit_codes.ERROR_OTHER

        return None

    def _parse_log_pymatgen(self, log_file_path):
        """Pymatgen parsing unused: less robust and powerful than cclib"""

        outobj = mgaus.GaussianOutput(log_file_path)
        parsed_dict = outobj.as_dict()

        # in case of geometry optimization, return the geometry as a separated node
        if 'opt' in parsed_dict['input']['route']:
            structure = StructureData(pymatgen_molecule=outobj.final_structure)
            self.out('output_structure', structure)

        self.out("output_parameters", Dict(dict=parsed_dict))

        with open(log_file_path, 'r') as logf:
            log_file = logf.read()

        if "Convergence failure -- run terminated." in log_file:
            return self.exit_codes.ERROR_SCF_FAILURE

        # Any other error...
        if "Error termination" in log_file:
            return self.exit_codes.ERROR_OTHER

        return None
