# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import io
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

NUM_RE = r"[-+]?(?:[0-9]*[.])?[0-9]+(?:[eE][-+]?\d+)?"


class GaussianBaseParser(Parser):
    """
    Basic AiiDA parser for the output of Gaussian
    
    Parses default cclib output as 'output_parameters' node and separates final SCF
    energy as 'energy_ev' and output structure as 'output_structure' (if applicable)
    """

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        try:
            out_folder = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        fname = self.node.process_class.OUTPUT_FILE

        if fname not in out_folder.list_object_names():
            return self.exit_codes.ERROR_OUTPUT_MISSING

        try:
            log_file_string = out_folder.get_object_content(fname)
        except IOError:
            return self.exit_codes.ERROR_OUTPUT_LOG_READ

        exit_code = self._parse_log(log_file_string, self.node.inputs)

        if exit_code is not None:
            return exit_code

        return ExitCode(0)

    def _parse_log(self, log_file_string, inputs):

        # parse with cclib
        property_dict = self._parse_log_cclib(log_file_string)

        if property_dict is None:
            return self.exit_codes.ERROR_OUTPUT_PARSING

        property_dict.update(self._parse_electron_numbers(log_file_string))

        # set output nodes
        self.out("output_parameters", Dict(dict=property_dict))

        if 'scfenergies' in property_dict:
            self.out("energy_ev", Float(property_dict['scfenergies'][-1]))

        self._set_output_structure(inputs, property_dict)

        exit_code = self._final_checks_on_log(log_file_string, property_dict)
        if exit_code is not None:
            return exit_code

        return None

    def _parse_electron_numbers(self, log_file_string):

        find_el = re.search(r"({0})\s*alpha electrons\s*({0}) beta".format(NUM_RE), log_file_string)

        if find_el is not None:
            return {'num_electrons': [int(e) for e in find_el.groups()]}
        else:
            return {}

    def _parse_log_cclib(self, log_file_string):

        data = cclib.io.ccread(io.StringIO(log_file_string))

        if data is None:
            return None

        property_dict = data.getattributes()

        # replace the first delta-energy of nan with zero
        # as nan is not allowed in AiiDA nodes
        if 'scfvalues' in property_dict:
            property_dict['scfvalues'] = [np.nan_to_num(svs) for svs in property_dict['scfvalues']]

        return property_dict

    def _set_output_structure(self, inputs, property_dict):
        # in case of geometry optimization,
        # return the last geometry as a separated node
        if "atomcoords" in property_dict:
            if (
                'opt' in inputs.parameters['route_parameters'] or
                len(property_dict["atomcoords"]) > 1
            ):

                opt_coords = property_dict["atomcoords"][-1]

                # The StructureData output node needs a cell,
                # even though it is not used in gaussian.
                # Set it arbitrarily as double the bounding box + 10
                double_bbox = 2 * np.ptp(opt_coords, axis=0) + 10

                ase_opt = ase.Atoms(
                    property_dict["atomnos"],
                    positions=property_dict["atomcoords"][-1],
                    cell=double_bbox
                )

                structure = StructureData(ase=ase_opt)
                self.out('output_structure', structure)

    def _final_checks_on_log(self, log_file_string, property_dict):

        # Error related to the symmetry identification (?).
        if "Logic error in ASyTop." in log_file_string:
            return self.exit_codes.ERROR_ASYTOP

        if "Inaccurate quadrature in CalDSu." in log_file_string:
            return self.exit_codes.ERROR_INACCURATE_QUADRATURE_CALDSU

        if "Convergence failure -- run terminated." in log_file_string:
            return self.exit_codes.ERROR_SCF_FAILURE

        if "Error termination" in log_file_string:
            return self.exit_codes.ERROR_TERMINATION

        if 'success' not in property_dict['metadata'] or not property_dict['metadata']['success']:
            return self.exit_codes.ERROR_NO_NORMAL_TERMINATION

        return None


class GaussianAdvancedParser(GaussianBaseParser):
    """
    Advanced AiiDA parser for the output of Gaussian
    """

    def _parse_log(self, log_file_string, inputs):
        """ Overwrite the basic log parser """

        # parse with cclib
        property_dict = self._parse_log_cclib(log_file_string)

        if property_dict is None:
            return self.exit_codes.ERROR_OUTPUT_PARSING

        property_dict.update(self._parse_electron_numbers(log_file_string))

        # Add spin expectations in property_dict
        property_dict.update(self._parse_log_spin_exp(log_file_string))

        # separate HOMO-LUMO gap as its own entry in property_dict
        self._extract_homo_lumo_gap(property_dict)

        # set output nodes
        self.out("output_parameters", Dict(dict=property_dict))

        if 'scfenergies' in property_dict:
            self.out("energy_ev", Float(property_dict['scfenergies'][-1]))

        self._set_output_structure(inputs, property_dict)

        exit_code = self._final_checks_on_log(log_file_string, property_dict)
        if exit_code is not None:
            return exit_code

        return None

    def _parse_log_spin_exp(self, log_file_string):
        """ Parse spin expectation values """

        spin_pattern = "\n <Sx>= ({0}) <Sy>= ({0}) <Sz>= ({0}) <S\\*\\*2>= ({0}) S= ({0})".format(
            NUM_RE
        )
        spin_list = []

        for spin_line in re.findall(spin_pattern, log_file_string):
            spin_list.append({
                'Sx': float(spin_line[0]),
                'Sy': float(spin_line[1]),
                'Sz': float(spin_line[2]),
                'S**2': float(spin_line[3]),
                'S': float(spin_line[4]),
            })

        return {'spin_expectation_values': spin_list}

    def _extract_homo_lumo_gap(self, property_dict):
        if 'moenergies' in property_dict and 'homos' in property_dict:
            nspin = len(property_dict['homos'])
            mo_e = np.array(property_dict['moenergies'])

            # if either HOMO is negative, such as in the case of H, don't extract gap
            if any([h < 0 for h in property_dict['homos']]):
                return
            try:
                if nspin == 1:
                    ih_s0 = property_dict['homos'][0]
                    property_dict['gap'] = mo_e[0][ih_s0 + 1] - mo_e[0][ih_s0]
                elif nspin == 2:
                    ih_s0 = property_dict['homos'][0]
                    ih_s1 = property_dict['homos'][1]
                    max_homo = np.max([mo_e[0, ih_s0], mo_e[1, ih_s1]])
                    min_lumo = np.min([mo_e[0, ih_s0 + 1], mo_e[1, ih_s1 + 1]])
                    # effective gap:
                    property_dict['gap'] = min_lumo - max_homo
                    # gaps for each spin channel separately:
                    property_dict['gap_a'] = (mo_e[0, ih_s0 + 1] - mo_e[0, ih_s0])
                    property_dict['gap_b'] = (mo_e[1, ih_s1 + 1] - mo_e[1, ih_s1])
            except IndexError:
                # In some cases, such as a very small basis set,
                # the parsed MOs don't include LUMO and an IndexError is raised.
                # Just skip the gap determination in this case
                pass
