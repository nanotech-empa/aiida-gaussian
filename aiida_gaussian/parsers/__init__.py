# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import io
import os

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict, StructureData
import pymatgen.io.gaussian as mgaus

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
            raise OutputParsingError("Gaussian output file not retrieved")

        outobj = mgaus.GaussianOutput(os.path.join(out_folder._repository._get_base_folder().abspath, fname))
        print(outobj.final_structure)
        try:
            structure = StructureData(pymatgen_molecule=outobj.final_structure)
            self.out('output_structure', structure)
        except Exception:  # pylint: disable=broad-except
            pass

        self._parse_stdout(outobj)

        return ExitCode(0)

    def _parse_stdout(self, outobj):
        """Basic Gaussian output file parser"""
        output_dict = {}
        output_dict['final_energy'] = outobj.final_energy
        output_dict['energy_unit'] = 'Hartree'

        self.out("output_parameters", Dict(dict=output_dict))
