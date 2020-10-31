# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import tempfile
import numpy as np

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict, StructureData, ArrayData

import matplotlib.pyplot as plt

from aiida_gaussian.utils.cube import Cube


class CubegenBaseParser(Parser):
    """Cubegen parser that created 2d slices of the generated cube files"""
    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        try:
            out_folder = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        out_folder_path = out_folder._repository._get_base_folder().abspath

        for retr_file in out_folder._repository.list_object_names():
            if retr_file.endswith(".cube"):
                cube_file_path = os.path.join(out_folder_path, retr_file)

                cube = Cube()
                cube.read_cube_file(cube_file_path)

                out_array = ArrayData()

                for h in np.arange(0.0, 10.0, 1.0):
                    try:
                        cube_plane = cube.get_plane_above_topmost_atom(h)
                        out_array.set_array('z_h%d' % int(h), cube_plane)
                    except IndexError:
                        break

                out_node_label = "cube_" + retr_file.split('.')[0].replace(
                    '-', '').replace('+', '')
                self.out(out_node_label, out_array)

        return ExitCode(0)
