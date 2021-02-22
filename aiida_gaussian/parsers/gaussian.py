# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import tempfile
import numpy as np

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict, StructureData, Float

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

        exit_code = self._parse_log(log_file_path, self.node.inputs)

        if exit_code is not None:
            return exit_code

        return ExitCode(0)

    def _parse_log(self, log_file_path, inputs):

        # parse with cclib
        property_dict = self._parse_log_cclib(log_file_path)

        # Extra stuff that cclib doesn't parse
        property_dict.update(self._parse_log_spin_exp(log_file_path))

        # set output nodes
        self.out("output_parameters", Dict(dict=property_dict))

        if 'scfenergies' in property_dict:
            self.out("energy_ev", Float(property_dict['scfenergies'][-1]))

        # in case of geometry optimization,
        # return the last geometry as a separated node
        if "atomcoords" in property_dict:

            if ('opt' in inputs.parameters['route_parameters']
                    or len(property_dict["atomcoords"]) > 1):

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

        if "Error termination" in log_file:
            return self.exit_codes.ERROR_TERMINATION

        if ('success' not in property_dict['metadata']
                or not property_dict['metadata']['success']):
            return self.exit_codes.ERROR_NO_NORMAL_TERMINATION

        return None

    def _parse_log_cclib(self, log_file_path):

        data = cclib.io.ccread(log_file_path)

        if data is None:
            return self.exit_codes.ERROR_OUTPUT_PARSING

        property_dict = data.getattributes()

        # replace the first delta-energy of nan with zero
        # as nan is not allowed in AiiDA nodes
        if 'scfvalues' in property_dict:
            property_dict['scfvalues'] = [
                np.nan_to_num(svs) for svs in property_dict['scfvalues']
            ]

        return property_dict

    def _parse_log_spin_exp(self, log_file_path):
        """ Parse spin expectation values """

        num_pattern = "[-+]?(?:[0-9]*[.])?[0-9]+(?:[eE][-+]?\d+)?"

        spin_pattern = "\n <Sx>= ({0}) <Sy>= ({0}) <Sz>= ({0}) <S\*\*2>= ({0}) S= ({0})".format(
            num_pattern)
        spin_list = []

        with open(log_file_path, 'r') as f:
            for spin_line in re.findall(spin_pattern, f.read()):
                spin_list.append({
                    'Sx': float(spin_line[0]),
                    'Sy': float(spin_line[1]),
                    'Sz': float(spin_line[2]),
                    'S**2': float(spin_line[3]),
                    'S': float(spin_line[4]),
                })

        return {'spin_expectation_values': spin_list}
