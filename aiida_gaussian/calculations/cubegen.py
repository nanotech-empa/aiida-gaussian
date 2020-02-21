# -*- coding: utf-8 -*-
"""Gaussian input plugin."""
from __future__ import absolute_import
import os
from shutil import copyfile, copytree
import six
from six.moves import map, range

from aiida.orm import Dict, FolderData, List, RemoteData, SinglefileData, Str, Int, Bool
from aiida.common import CalcInfo, CodeInfo, InputValidationError
from aiida.engine import CalcJob
from aiida.plugins import DataFactory


class CubegenCalculation(CalcJob):
    """
    Plugin to run the cubegen utility

    Example:

    parameters = {
        "homo-5": {
            "kind": "AMO=16",
            "npts": -2,
        },
        "spin": {
            "kind": "Spin=SCF",
            "npts": 0,
        },
    }
    Each key corresponds to one produced cube.
    key specifies the name of the output node
    """

    _DEFAULT_INPUT_FILE = "aiida.fchk"
    _PARENT_FOLDER_NAME = "parent_calc"

    @classmethod
    def define(cls, spec):
        super(CubegenCalculation, cls).define(spec)

        spec.input("parameters", valid_type=Dict, required=True, help='dictionary containing entries for cubes to be printed.')
        spec.input('parent_calc_folder', valid_type=RemoteData, required=True, help='the folder of a containing the .fchk')

        spec.input('retrieve_cubes', valid_type=Bool, required=False, default=Bool(False), help='should the cube be retrieved?')
        spec.input("gauss_memdef", valid_type=Int, required=False, default=Int(1024), help="Set the GAUSS_MEMDEF env variable to set the max memory in MB.")

        # Turn mpi off by default
        spec.input('metadata.options.withmpi', valid_type=bool, default=False)

    # --------------------------------------------------------------------------
    # pylint: disable = too-many-locals
    def prepare_for_submission(self, folder):
        
         # create calculation info
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.codes_info = []
        calcinfo.retrieve_list = []

        for key, params in self.inputs.parameters.get_dict().items():
            
            cube_name = key+".cube"
            kind_str = params["kind"]
            npts = params["npts"]

            # create code info 
            codeinfo = CodeInfo()

            codeinfo.cmdline_params = []
            codeinfo.cmdline_params.append(str(self.inputs.metadata.options.resources['tot_num_mpiprocs']))
            codeinfo.cmdline_params.append(kind_str)
            codeinfo.cmdline_params.append(self._PARENT_FOLDER_NAME + "/" + self._DEFAULT_INPUT_FILE)
            codeinfo.cmdline_params.append(cube_name)
            codeinfo.cmdline_params.append(str(npts))

            codeinfo.code_uuid = self.inputs.code.uuid
            codeinfo.withmpi = self.inputs.metadata.options.withmpi

            calcinfo.codes_info.append(codeinfo)

            if self.inputs.retrieve_cubes.value:
                calcinfo.retrieve_list.append(cube_name)

        extra_prepend = "\nexport GAUSS_MEMDEF=%dMB\n" % self.inputs.gauss_memdef
        if not hasattr(calcinfo, 'prepend_text') or not calcinfo.prepend_text:
            calcinfo.prepend_text = extra_prepend
        else:
            calcinfo.prepend_text += extra_prepend

         # symlink or copy to parent calculation
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        comp_uuid = self.inputs.parent_calc_folder.computer.uuid
        remote_path = self.inputs.parent_calc_folder.get_remote_path()
        copy_info = (comp_uuid, remote_path, self._PARENT_FOLDER_NAME)
        if self.inputs.code.computer.uuid == comp_uuid:  # if running on the same computer - make a symlink
            # if not - copy the folder
            calcinfo.remote_symlink_list.append(copy_info)
        else:
            calcinfo.remote_copy_list.append(copy_info)
        

        return calcinfo
