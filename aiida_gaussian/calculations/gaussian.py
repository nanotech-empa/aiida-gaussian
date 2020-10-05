# -*- coding: utf-8 -*-
"""Gaussian input plugin."""
from __future__ import absolute_import
import os
from shutil import copyfile, copytree
import six
from six.moves import map, range

from aiida.orm import Dict, FolderData, List, RemoteData, SinglefileData
from aiida.common import CalcInfo, CodeInfo, InputValidationError

# from aiida.cmdline.utils import echo
from aiida.engine import CalcJob
from aiida.plugins import DataFactory

import pymatgen as mg
import pymatgen.io.gaussian as mgaus

StructureData = DataFactory("structure")


class GaussianCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping Gaussian
    
    Template:

    parameters = Dict(dict={
        'link0_parameters': {
            '%chk':'aiida.chk',
            '%mem': '1024MB',
            '%nprocshared': '2',
        },
        'functional':'PBE1PBE',
        'basis_set':'6-31g',
        'charge': 0,
        'multiplicity': 1,
        'route_parameters': {
            'scf': {'cdiis': None}
            'nosymm': None,
            'opt': 'tight',
        },
    })

    """

    # Defaults
    INPUT_FILE = "aiida.inp"
    OUTPUT_FILE = "aiida.out"
    DEFAULT_PARSER = "gaussian_base_parser"

    @classmethod
    def define(cls, spec):
        super(GaussianCalculation, cls).define(spec)

        # Input parameters
        spec.input(
            "structure",
            valid_type=StructureData,
            required=False,
            help="Input structure; will be converted to pymatgen object",
        )

        spec.input("parameters",
                   valid_type=Dict,
                   required=True,
                   help="Input parameters")
        spec.input(
            "settings",
            valid_type=Dict,
            required=False,
            help="additional input parameters",
        )

        spec.input(
            "parent_calc_folder",
            valid_type=RemoteData,
            required=False,
            help="the folder of a completed gaussian calculation",
        )

        spec.input_namespace(
            "extra_link1_sections",
            valid_type=Dict,
            required=False,
            dynamic=True,
            help="parameters for extra link1 sections",
        )

        # Turn mpi off by default
        spec.input("metadata.options.withmpi", valid_type=bool, default=False)

        spec.input(
            "metadata.options.parser_name",
            valid_type=six.string_types,
            default=cls.DEFAULT_PARSER,
            non_db=True,
        )

        # Outputs
        spec.output(
            "output_parameters",
            valid_type=Dict,
            required=True,
            help="The result parameters of the calculation",
        )
        spec.output(
            "output_structure",
            valid_type=StructureData,
            required=False,
            help="Final optimized structure, if available",
        )

        spec.default_output_node = "output_parameters"
        spec.outputs.dynamic = True

        # Exit codes
        spec.exit_code(
            100,
            "ERROR_MISSING_OUTPUT_FILES",
            message="Calculation did not produce all expected output files.",
        )

    # --------------------------------------------------------------------------
    # pylint: disable = too-many-locals
    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """
        # create calc info
        calcinfo = CalcInfo()
        calcinfo.remote_copy_list = []
        calcinfo.local_copy_list = []

        # The main input
        try:
            input_string = GaussianCalculation._render_input_string_from_params(
                self.inputs.parameters.get_dict(), self.inputs.structure)
        # If structure is not specified the user might want to restart from a chk
        except AttributeError:
            input_string = GaussianCalculation._render_input_string_from_params(
                self.inputs.parameters.get_dict(), None)

        # Parse additional link1 sections
        if "extra_link1_sections" in self.inputs:
            for l1_name, l1_params in self.inputs.extra_link1_sections.items():
                input_string += "--Link1--\n"
                # The link1 secions don't support their own geometries.
                input_string += GaussianCalculation._render_input_string_from_params(
                    l1_params.get_dict(), None)

        with open(folder.get_abs_path(self.INPUT_FILE), "w") as out_file:
            out_file.write(input_string)

        settings = self.inputs.settings.get_dict(
        ) if "settings" in self.inputs else {}

        # create code info
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop("cmdline", [])
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdin_name = self.INPUT_FILE
        codeinfo.stdout_name = self.OUTPUT_FILE
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # create calculation info
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self.INPUT_FILE
        calcinfo.stdout_name = self.OUTPUT_FILE
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = [self.OUTPUT_FILE]

        # symlink or copy to parent calculation
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        if "parent_calc_folder" in self.inputs:
            comp_uuid = self.inputs.parent_calc_folder.computer.uuid
            remote_path = self.inputs.parent_calc_folder.get_remote_path()
            copy_info = (comp_uuid, remote_path, "parent_calc")
            if (self.inputs.code.computer.uuid == comp_uuid
                ):  # if running on the same computer - make a symlink
                # if not - copy the folder
                calcinfo.remote_symlink_list.append(copy_info)
            else:
                calcinfo.remote_copy_list.append(copy_info)

        return calcinfo

    @classmethod
    def _render_input_string_from_params(cls, param_dict, structure):

        # the structure
        pmg_mol = structure.get_pymatgen_molecule() if structure else None

        # Determine charge and multiplicity
        charge = param_dict[
            "charge"] if "charge" in param_dict else pmg_mol.charge
        multiplicity = (param_dict["multiplicity"] if
                        "multiplicity" in param_dict else pmg_mol.multiplicity)

        inp = mgaus.GaussianInput(
            pmg_mol,
            charge=charge,
            spin_multiplicity=multiplicity,
            title="input generated by the aiida-gaussian plugin",
            functional=param_dict.get(
                "functional"),  # dict.get returns None if key is not in dict
            basis_set=param_dict.get("basis_set"),
            route_parameters=param_dict.get("route_parameters"),
            input_parameters=param_dict.get("input_parameters"),
            link0_parameters=param_dict.get("link0_parameters"),
            dieze_tag="#P",
        )

        return inp.to_string(cart_coords=True)
