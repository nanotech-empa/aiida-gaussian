# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import tempfile

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
            return self.exit_codes.ERROR_OUTPUT_MISSING

        log_file_path = os.path.join(
            out_folder._repository._get_base_folder().abspath, fname)

        outobj = mgaus.GaussianOutput(log_file_path)
        parsed_dict = outobj.as_dict()

        # in case of geometry optimization, return the geometry as a separated node
        if 'opt' in parsed_dict['input']['route']:
            structure = StructureData(pymatgen_molecule=outobj.final_structure)
            self.out('output_structure', structure)

        self.out("output_parameters", Dict(dict=parsed_dict))

        return ExitCode(0)
