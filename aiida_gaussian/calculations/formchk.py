# -*- coding: utf-8 -*-
"""Gaussian formchk plugin."""
from __future__ import absolute_import

from aiida.orm import List, RemoteData, SinglefileData, Str, Bool
from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob


class FormchkCalculation(CalcJob):
    """
    Very simple plugin to run the formchk utility
    """

    DEFAULT_INPUT_FILE = "aiida.chk"
    DEFAULT_OUTPUT_FILE = "aiida.fchk"
    PARENT_FOLDER_NAME = "parent_calc"

    @classmethod
    def define(cls, spec):
        super(FormchkCalculation, cls).define(spec)

        spec.input(
            'parent_calc_folder',
            valid_type=RemoteData,
            required=True,
            help='the folder of a containing the .chk'
        )
        spec.input(
            'chk_name',
            valid_type=Str,
            required=False,
            default=lambda: Str(cls.DEFAULT_INPUT_FILE),
            help="name of the checkpoint file"
        )
        spec.input(
            'retrieve_fchk',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(False),
            help="retrieve the fchk file"
        )

        # Turn mpi off by default
        spec.input('metadata.options.withmpi', valid_type=bool, default=False)

    # --------------------------------------------------------------------------
    def prepare_for_submission(self, folder):

        # create code info
        codeinfo = CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = [
            self.PARENT_FOLDER_NAME + "/" + self.inputs.chk_name.value, self.DEFAULT_OUTPUT_FILE
        ]
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # create calculation info
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = []

        if self.inputs.retrieve_fchk:
            calcinfo.retrieve_list.append(self.DEFAULT_OUTPUT_FILE)

        # symlink or copy to parent calculation
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        comp_uuid = self.inputs.parent_calc_folder.computer.uuid
        remote_path = self.inputs.parent_calc_folder.get_remote_path()
        copy_info = (comp_uuid, remote_path, self.PARENT_FOLDER_NAME)
        if self.inputs.code.computer.uuid == comp_uuid:  # if running on the same computer - make a symlink
            # if not - copy the folder
            calcinfo.remote_symlink_list.append(copy_info)
        else:
            calcinfo.remote_copy_list.append(copy_info)

        return calcinfo
