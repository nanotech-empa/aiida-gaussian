# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import numpy as np

from aiida.parsers import Parser
from aiida.common import NotExistent
from aiida.engine import ExitCode
from aiida.orm import ArrayData

from aiida_gaussian.utils.cube import Cube


class CubegenBaseParser(Parser):
    """Cubegen parser that creates 2d slices of the generated cube files"""
    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        retrieved_folder_paths = []

        try:
            retrieved_folder = self.retrieved
            retrieved_folder_paths.append(
                retrieved_folder._repository._get_base_folder().abspath)
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        retrieve_temp_list_input = self.node.get_attribute(
            'retrieve_temporary_list', None)
        # If temporary files were specified, check that we have them
        if retrieve_temp_list_input:
            try:
                retrieved_temp_folder_path = kwargs[
                    'retrieved_temporary_folder']
                retrieved_folder_paths.append(retrieved_temp_folder_path)
            except KeyError:
                return self.exit(
                    self.exit_codes.ERROR_NO_RETRIEVED_TEMPORARY_FOLDER)

        if "parser_params" in self.node.inputs:
            parser_params = dict(self.node.inputs.parser_params)
        else:
            parser_params = {}

        self._parse_folders(retrieved_folder_paths, parser_params)

        return ExitCode(0)

    def _parse_folders(self, retrieved_folder_paths, parser_params):

        for folder_path in retrieved_folder_paths:
            for filename in os.listdir(folder_path):
                filepath = os.path.join(folder_path, filename)

                if filename.endswith(".cube"):

                    cube = Cube()
                    cube.read_cube_file(filepath)

                    out_array = ArrayData()

                    for h in np.arange(0.0, 10.0, 1.0):
                        try:
                            cube_plane = cube.get_plane_above_topmost_atom(h)
                            out_array.set_array('z_h%d' % int(h), cube_plane)
                        except IndexError:
                            break

                    out_node_label = "cube_" + filename.split('.')[0].replace(
                        '-', '').replace('+', '')
                    self.out(out_node_label, out_array)
