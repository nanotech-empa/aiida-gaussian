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
            raise OutputParsingError("Gaussian output file not retrieved")

        with open(
                os.path.join(out_folder._repository._get_base_folder().abspath,
                             fname), 'r') as log_file:
            full_output_log = log_file.read()

        # Split the output log according to link1 sections
        output_log_split = [""]
        for line_i, log_line in enumerate(full_output_log.splitlines()):
            output_log_split[-1] += log_line + "\n"
            if "Normal termination" in log_line:
                output_log_split.append("")
        output_log_split = output_log_split[:-1]

        for section_i, out_log in enumerate(output_log_split):
            # pymatgen can only parse files,
            # so create temporary ones for each link1 log section
            tempf = tempfile.NamedTemporaryFile(delete=False, mode='w')
            tempf.write(out_log)
            tempf.close()
            outobj = mgaus.GaussianOutput(tempf.name)
            parsed_dict = outobj.as_dict()

            # in case of main section, don't add prefix
            output_prefix = ""
            if section_i > 0:
                output_prefix = "link1_sec%d_" % section_i

            # in case of geometry optimization, return the geometry as a separated node
            if 'opt' in parsed_dict['input']['route']:
                structure = StructureData(
                    pymatgen_molecule=outobj.final_structure)
                self.out('%soutput_structure' % output_prefix, structure)

            self.out("%soutput_parameters" % output_prefix,
                     Dict(dict=parsed_dict))

        return ExitCode(0)
