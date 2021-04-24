# -*- coding: utf-8 -*-
"""Gaussian input plugin."""
from __future__ import absolute_import

from aiida.orm import Dict, RemoteData, Str, Int, Bool, SinglefileData
from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob


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

    In case of "npts": -1, you have to use the stencil file input:

        IFlag X0 Y0 Z0  # Output unit number and initial point.
        N1 X1 Y1 Z1     # Number of points and step-size in the X-direction.
        N2 X2 Y2 Z2     # Number of points and step-size in the Y-direction.
        N3 X3 Y3 Z3     # Number of points and step-size in the Z-direction.

    See more details at https://gaussian.com/cubegen/
    """

    DEFAULT_INPUT_FILE = "aiida.fchk"
    PARENT_FOLDER_NAME = "parent_calc"
    DEFAULT_PARSER = "gaussian.cubegen_base"

    @classmethod
    def define(cls, spec):
        super(CubegenCalculation, cls).define(spec)

        spec.input(
            "parameters",
            valid_type=Dict,
            required=True,
            help='dictionary containing entries for cubes to be printed.'
        )

        spec.input(
            'parent_calc_folder',
            valid_type=RemoteData,
            required=True,
            help='the folder of a containing the .fchk'
        )

        spec.input(
            "stencil",
            valid_type=SinglefileData,
            required=False,
            help="In case of npts=-1, use this cube specification.",
        )

        spec.input(
            'retrieve_cubes',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(False),
            help='should the cubes be retrieved?'
        )

        spec.input(
            "gauss_memdef",
            valid_type=Int,
            required=False,
            default=lambda: Int(1024),
            help="Set the GAUSS_MEMDEF env variable to set the max memory in MB."
        )

        # Turn mpi off by default
        spec.input('metadata.options.withmpi', valid_type=bool, default=False)

        spec.input(
            "metadata.options.parser_name",
            valid_type=str,
            default=cls.DEFAULT_PARSER,
            non_db=True,
        )

        spec.inputs.dynamic = True
        spec.outputs.dynamic = True

        # Exit codes
        spec.exit_code(
            300,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder could not be accessed.",
        )

        spec.exit_code(
            301,
            "ERROR_NO_RETRIEVED_TEMPORARY_FOLDER",
            message="The retrieved temporary folder could not be accessed.",
        )

    # --------------------------------------------------------------------------
    def prepare_for_submission(self, folder):

        # create calculation info
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.codes_info = []
        calcinfo.retrieve_list = []
        calcinfo.retrieve_temporary_list = []
        calcinfo.prepend_text = "export GAUSS_MEMDEF=%dMB\n" % self.inputs.gauss_memdef

        calcinfo.local_copy_list = []

        if "stencil" in self.inputs:
            calcinfo.local_copy_list.append(
                (self.inputs.stencil.uuid, self.inputs.stencil.filename, 'stencil.txt')
            )

        for key, params in self.inputs.parameters.get_dict().items():

            cube_name = key + ".cube"
            kind_str = params["kind"]
            npts = params["npts"]

            # create code info
            codeinfo = CodeInfo()

            codeinfo.cmdline_params = []
            codeinfo.cmdline_params.append(
                str(self.inputs.metadata.options.resources['tot_num_mpiprocs'])
            )
            codeinfo.cmdline_params.append(kind_str)
            codeinfo.cmdline_params.append(self.PARENT_FOLDER_NAME + "/" + self.DEFAULT_INPUT_FILE)
            codeinfo.cmdline_params.append(cube_name)

            if npts == -1:
                if 'stencil' not in self.inputs:
                    self.report("Warning: npts: -1 set but no stencil provided, using -2")
                    codeinfo.cmdline_params.append("-2")
                else:
                    codeinfo.cmdline_params.append(str(npts))
                    codeinfo.stdin_name = "stencil.txt"
            else:
                codeinfo.cmdline_params.append(str(npts))

            codeinfo.code_uuid = self.inputs.code.uuid
            codeinfo.withmpi = self.inputs.metadata.options.withmpi

            calcinfo.codes_info.append(codeinfo)

            if self.inputs.retrieve_cubes.value:
                calcinfo.retrieve_list.append(cube_name)
            else:
                calcinfo.retrieve_temporary_list.append(cube_name)

        # symlink or copy to parent calculation
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        comp_uuid = self.inputs.parent_calc_folder.computer.uuid
        remote_path = self.inputs.parent_calc_folder.get_remote_path()
        copy_info = (comp_uuid, remote_path, self.PARENT_FOLDER_NAME)
        if self.inputs.code.computer.uuid == comp_uuid:
            # if running on the same computer - make a symlink
            # if not - copy the folder
            calcinfo.remote_symlink_list.append(copy_info)
        else:
            calcinfo.remote_copy_list.append(copy_info)

        return calcinfo
