# -*- coding: utf-8 -*-
"""AiiDA-Gaussian output parser"""
from __future__ import absolute_import

import os
import numpy as np

from aiida.parsers import Parser
from aiida.common import NotExistent
from aiida.engine import ExitCode
from aiida.orm import ArrayData, FolderData

from aiida_gaussian.utils.cube import Cube


class CubegenBaseParser(Parser):
    """Cubegen parser that creates 2d slices of the generated cube files"""

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        retrieved_folders = []

        try:
            retrieved_folder = self.retrieved
            retrieved_folders.append(retrieved_folder)
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        retrieve_temp_list_input = self.node.get_attribute('retrieve_temporary_list', None)
        # If temporary files were specified, check that we have them
        if retrieve_temp_list_input:
            try:
                retrieved_temp_folder_path = kwargs['retrieved_temporary_folder']
                # create a folderdata object to treat this the same way
                temp_fd = FolderData(tree=retrieved_temp_folder_path)
                retrieved_folders.append(temp_fd)
            except KeyError:
                return self.exit_codes.ERROR_NO_RETRIEVED_TEMPORARY_FOLDER

        if "parser_params" in self.node.inputs:
            parser_params = dict(self.node.inputs.parser_params)
        else:
            parser_params = {}

        self._parse_folders(retrieved_folders, parser_params)

        return ExitCode(0)

    def _parse_folders(self, retrieved_folders, parser_params):

        if 'heights' in parser_params:
            heights = parser_params['heights']
        else:
            heights = [2.0]

        # By default, don't re-orient cube
        orient_cube = False
        if 'orient_cube' in parser_params:
            orient_cube = parser_params['orient_cube']

        out_array = ArrayData()

        add_suppl = True

        for retrieved_fd in retrieved_folders:
            for filename in retrieved_fd.list_object_names():
                if filename.endswith(".cube"):

                    with retrieved_fd.open(filename) as handle:
                        cube = Cube.from_file_handle(handle)

                    if orient_cube:
                        self._orient_cube(cube)

                    cube_data = None
                    h_added = []

                    for h in heights:
                        try:
                            cube_plane = cube.get_plane_above_topmost_atom(h)
                            cube_plane = np.expand_dims(cube_plane, axis=2)
                            if cube_data is None:
                                cube_data = cube_plane
                            else:
                                cube_data = np.concatenate((cube_data, cube_plane), axis=2)
                            h_added.append(h)
                        except IndexError:
                            pass

                    if cube_data is None:
                        # None of the heights were inside the calculated box
                        return

                    arr_label = "cube_" + os.path.splitext(filename)[0].replace('-', ''
                                                                                ).replace('+', '')

                    out_array.set_array(arr_label, cube_data)

                    if add_suppl:
                        out_array.set_array('x_arr', cube.x_arr_ang)
                        out_array.set_array('y_arr', cube.y_arr_ang)
                        out_array.set_array('h_arr', np.array(h_added))
                        add_suppl = False

        self.out('cube_planes_array', out_array)

    def _orient_cube(self, cube):
        """Swap cube axes such that 
        index 0 has the longest-spanning dimension
        index 2 has the "flattest" dimension
        """
        ptp = np.ptp(cube.ase_atoms.positions, axis=0)
        i_max = np.argmax(ptp)
        if i_max != 0:
            cube.swapaxes(0, i_max)
        ptp = np.ptp(cube.ase_atoms.positions, axis=0)
        i_min = np.argmin(ptp)
        if i_min != 2:
            cube.swapaxes(2, i_min)