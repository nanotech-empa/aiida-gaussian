"""Gaussian input plugin."""

from aiida.common import CalcInfo, CodeInfo

# from aiida.cmdline.utils import echo
from aiida.engine import CalcJob
from aiida.orm import Dict, Float, RemoteData
from aiida.plugins import DataFactory
from pymatgen.io.gaussian import GaussianInput

StructureData = DataFactory("core.structure")


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
    PARENT_FOLDER_NAME = "parent_calc"
    DEFAULT_PARSER = "gaussian.base"

    @classmethod
    def define(cls, spec):
        super().define(spec)

        # Input parameters
        spec.input(
            "structure",
            valid_type=StructureData,
            required=False,
            help="Input structure; will be converted to pymatgen object",
        )

        spec.input(
            "parameters", valid_type=Dict, required=True, help="Input parameters"
        )
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

        # Turn mpi off by default
        spec.input("metadata.options.withmpi", valid_type=bool, default=False)

        spec.input(
            "metadata.options.parser_name",
            valid_type=str,
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
        spec.output(
            "energy_ev",
            valid_type=Float,
            required=False,
            help="Final energy in electronvolts",
        )

        spec.default_output_node = "output_parameters"
        spec.outputs.dynamic = True

        # Exit codes
        spec.exit_code(
            200,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder data node could not be accessed.",
        )
        spec.exit_code(
            210,
            "ERROR_OUTPUT_MISSING",
            message="The retrieved folder did not contain the output file.",
        )
        spec.exit_code(
            211,
            "ERROR_OUTPUT_LOG_READ",
            message="The retrieved output log could not be read.",
        )
        spec.exit_code(
            220,
            "ERROR_OUTPUT_PARSING",
            message="The output file could not be parsed.",
        )
        spec.exit_code(
            301,
            "ERROR_SCF_FAILURE",
            message="The SCF did not converge and the calculation was terminated.",
        )
        spec.exit_code(
            302,
            "ERROR_ASYTOP",
            message="The calculation was terminated due to a logic error in ASyTop.",
        )
        spec.exit_code(
            303,
            "ERROR_INACCURATE_QUADRATURE_CALDSU",
            message="The calculation was terminated due to an inaccurate quadrature in CalDSu.",
        )
        spec.exit_code(
            390,
            "ERROR_TERMINATION",
            message="The calculation was terminated due to an error.",
        )
        spec.exit_code(
            391,
            "ERROR_NO_NORMAL_TERMINATION",
            message="The log did not contain 'Normal termination' (probably out of time).",
        )

    # --------------------------------------------------------------------------
    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        if "structure" in self.inputs:
            pmg_structure = self.inputs.structure.get_pymatgen_molecule()
        else:
            # If structure is not specified, it is read from the chk file
            pmg_structure = None

        # Generate the input file
        input_string = GaussianCalculation._render_input_string_from_params(
            self.inputs.parameters.get_dict(), pmg_structure
        )

        # Handle Ghost atoms (e.g. when doing NICS calculations)
        # Atoms with symbol 'X' in input structure are considered Ghost atoms.
        # Pymatgen converts these into `X0+` in the input script
        # and Gaussian needs these to be called `Bq`.
        if pmg_structure and "X0+" in pmg_structure.labels:
            input_string = input_string.replace("X0+", "Bq")

        with open(folder.get_abs_path(self.INPUT_FILE), "w") as out_file:
            out_file.write(input_string)

        settings = self.inputs.settings.get_dict() if "settings" in self.inputs else {}

        # create code info
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop("cmdline", [])
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdin_name = self.INPUT_FILE
        codeinfo.stdout_name = self.OUTPUT_FILE
        codeinfo.withmpi = self.inputs.metadata.options.withmpi

        # create calculation info
        calcinfo = CalcInfo()
        calcinfo.remote_copy_list = []
        calcinfo.local_copy_list = []
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
            copy_info = (comp_uuid, remote_path, self.PARENT_FOLDER_NAME)
            if self.inputs.code.computer.uuid == comp_uuid:
                # if running on the same computer - make a symlink
                # if not - copy the folder
                calcinfo.remote_symlink_list.append(copy_info)
            else:
                calcinfo.remote_copy_list.append(copy_info)

        return calcinfo

    @classmethod
    def _render_input_string_from_params(cls, parameters, pmg_structure):
        """Generate the Gaussian input file using pymatgen."""
        parameters.setdefault("dieze_tag", "#N")
        parameters.setdefault("spin_multiplicity", parameters.pop("multiplicity", None))
        parameters["title"] = "input generated by the aiida-gaussian plugin"
        gaussian_input = GaussianInput(pmg_structure, **parameters)
        try:
            return gaussian_input.to_string(cart_coords=True)
        except AttributeError:
            return gaussian_input.to_str(cart_coords=True)
