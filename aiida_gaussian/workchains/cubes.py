import io
import ase

import numpy as np

from aiida.engine import WorkChain, ToContext, ExitCode
from aiida.orm import Int, Float, Str, Bool, Code, Dict, List
from aiida.orm import SinglefileData, StructureData, RemoteData

from aiida.plugins import CalculationFactory

FormchkCalculation = CalculationFactory('gaussian.formchk')
CubegenCalculation = CalculationFactory('gaussian.cubegen')


class GaussianCubesWorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input("formchk_code", valid_type=Code)
        spec.input("cubegen_code", valid_type=Code)

        spec.input(
            'gaussian_calc_folder',
            valid_type=RemoteData,
            required=True,
            help='The gaussian calculation output folder.'
        )

        spec.input(
            'gaussian_output_params',
            valid_type=Dict,
            required=True,
            help='The gaussian calculation output parameters.'
        )

        spec.input(
            'orbital_indexes',
            valid_type=List,
            required=False,
            default=lambda: List(list=[0, 1]),
            help='Indexes of the orbital cubes to generate.'
        )

        spec.input(
            'orbital_index_ref',
            valid_type=Str,
            required=False,
            default=lambda: Str('half_num_el'),
            help="Reference index, possible choices: 'half_num_el', 'abs'."
        )

        spec.input(
            'natural_orbitals',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(False),
            help="The cube files are natural orbitals."
        )

        spec.input(
            'generate_density',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(True),
            help="Generate density cube."
        )

        spec.input(
            'generate_spin_density',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(True),
            help="Generate spin density cube (if applicable)."
        )

        spec.input(
            'edge_space',
            valid_type=Float,
            required=False,
            default=lambda: Float(3.0),
            help='Extra cube space in addition to molecule bounding box [ang].'
        )

        spec.input(
            'dx',
            valid_type=Float,
            required=False,
            default=lambda: Float(0.15),
            help='Cube file spacing [ang].'
        )

        spec.input(
            'retrieve_cubes',
            valid_type=Bool,
            required=False,
            default=lambda: Bool(False),
            help='should the cubes be retrieved?'
        )

        spec.input(
            "cubegen_parser_name",
            valid_type=str,
            default=CubegenCalculation.DEFAULT_PARSER,
            non_db=True,
        )

        spec.input(
            "cubegen_parser_params",
            valid_type=Dict,
            required=False,
            default=lambda: Dict(dict={}),
            help='Additional parameters to cubegen parser.'
        )

        spec.outline(cls.check_input, cls.formchk_step, cls.cubegen_step, cls.finalize)

        spec.outputs.dynamic = True

        spec.exit_code(
            302,
            "ERROR_INPUT",
            message="Input options are invalid.",
        )

        spec.exit_code(
            390,
            "ERROR_TERMINATION",
            message="One or more steps of the work chain failed.",
        )

    def _set_resources(self):
        res = {"tot_num_mpiprocs": 1}
        if 'lsf' not in self.inputs.formchk_code.computer.scheduler_type:
            # LSF scheduler doesn't work with 'num_machines'
            # other schedulers require num_machines
            res['num_machines'] = 1
        return res

    def _check_if_previous_calc_ok(self, prev_calc):
        if not prev_calc.is_finished_ok:
            if prev_calc.exit_status is not None and prev_calc.exit_status >= 500:
                self.report("Warning: previous step: " + str(prev_calc.exit_message))
            else:
                self.report("ERROR: previous step: " + str(prev_calc.exit_message))
                return False
        return True

    def check_input(self):
        if self.inputs.orbital_index_ref not in ('half_num_el', 'abs'):
            return self.exit_codes.ERROR_INPUT  # pylint: disable=no-member
        return ExitCode(0)

    def formchk_step(self):

        self.report("Running FormChk")

        builder = FormchkCalculation.get_builder()

        builder.parent_calc_folder = self.inputs.gaussian_calc_folder
        builder.code = self.inputs.formchk_code

        builder.metadata.options.resources = self._set_resources()

        builder.metadata.options.max_wallclock_seconds = 1 * 20 * 60

        future = self.submit(builder)
        return ToContext(formchk_node=future)

    def _get_orbital_label(self, i_orb_wrt_homo):
        if i_orb_wrt_homo < 0:
            label = "homo%+d" % i_orb_wrt_homo
        elif i_orb_wrt_homo == 0:
            label = "homo"
        elif i_orb_wrt_homo == 1:
            label = "lumo"
        elif i_orb_wrt_homo > 1:
            label = "lumo%+d" % (i_orb_wrt_homo - 1)
        return label

    def cubegen_step(self):

        if not self._check_if_previous_calc_ok(self.ctx.formchk_node):
            return self.exit_codes.ERROR_TERMINATION  # pylint: disable=no-member

        self.report("Running Cubegen")

        gout_params = dict(self.inputs.gaussian_output_params)

        # --------------------------------------------------------------
        # Create the stencil

        ase_atoms = ase.Atoms(gout_params['atomnos'], positions=gout_params['atomcoords'][0])

        es = self.inputs.edge_space.value + self.inputs.dx.value

        xmin = np.min(ase_atoms.positions[:, 0]) - es
        xmax = np.max(ase_atoms.positions[:, 0]) + es
        ymin = np.min(ase_atoms.positions[:, 1]) - es
        ymax = np.max(ase_atoms.positions[:, 1]) + es
        zmin = np.min(ase_atoms.positions[:, 2]) - es
        zmax = np.max(ase_atoms.positions[:, 2]) + es

        geom_center = np.array([xmin + xmax, ymin + ymax, zmin + zmax]) / 2.0

        cell = np.array([xmax - xmin, ymax - ymin, zmax - zmin])

        cell_n = (np.round(cell / self.inputs.dx.value)).astype(int)

        stencil = b"-1 %f %f %f\n" % tuple(geom_center - cell / 2)
        stencil += b"%d %f 0.0 0.0\n" % (cell_n[0], self.inputs.dx.value)
        stencil += b"%d 0.0 %f 0.0\n" % (cell_n[1], self.inputs.dx.value)
        stencil += b"%d 0.0 0.0 %f\n" % (cell_n[2], self.inputs.dx.value)

        # --------------------------------------------------------------
        # Create the parameters dict

        params_dict = {}

        orb_indexes = list(self.inputs.orbital_indexes)
        abs_orb_indexes = []

        if self.inputs.orbital_index_ref == 'half_num_el':

            total_num_electrons = sum(gout_params['num_electrons'])
            ref_index = total_num_electrons // 2

            for i_orb in orb_indexes:
                abs_orb_indexes.append(i_orb + ref_index)

        elif self.inputs.orbital_index_ref == 'abs':
            abs_orb_indexes = orb_indexes

        # remove negative and 0 indexes
        abs_orb_indexes = [i for i in abs_orb_indexes if i >= 1]

        for i_orb in abs_orb_indexes:

            if self.inputs.natural_orbitals:
                params_dict[f"{i_orb}_no"] = {
                    "kind": "MO=%d" % i_orb,
                    "npts": -1,
                }
            else:
                homos = gout_params['homos']
                # use the cubegen convention, where counting starts from 1
                homos = [h + 1 for h in homos]

                for i_spin, h in enumerate(homos):
                    label = self._get_orbital_label(i_orb - h)
                    if len(homos) == 1:
                        params_dict["%d_%s" % (i_orb, label)] = {
                            "kind": "MO=%d" % i_orb,
                            "npts": -1,
                        }
                    else:
                        spin_letter = "a" if i_spin == 0 else "b"
                        params_dict["%d_%s_%s" % (i_orb, spin_letter, label)] = {
                            "kind": "%sMO=%d" % (spin_letter.upper(), i_orb),
                            "npts": -1,
                        }

        if not self.inputs.natural_orbitals:
            if self.inputs.generate_density:
                params_dict['density'] = {
                    "kind": "Density=SCF",
                    "npts": -1,
                }
            if self.inputs.generate_spin_density:
                if 'homos' in gout_params and len(gout_params['homos']) == 2:
                    params_dict['spin'] = {
                        "kind": "Spin=SCF",
                        "npts": -1,
                    }

        # --------------------------------------------------------------
        # Create the builder and submit!

        builder = CubegenCalculation.get_builder()
        builder.parent_calc_folder = self.ctx.formchk_node.outputs.remote_folder
        builder.code = self.inputs.cubegen_code
        builder.stencil = SinglefileData(io.BytesIO(stencil))
        builder.parameters = Dict(params_dict)
        builder.retrieve_cubes = self.inputs.retrieve_cubes

        builder.parser_params = self.inputs.cubegen_parser_params

        builder.metadata.options.resources = self._set_resources()

        builder.metadata.options.max_wallclock_seconds = 2 * 60 * 60

        builder.metadata.options.parser_name = self.inputs.cubegen_parser_name

        future = self.submit(builder)
        return ToContext(cubegen_node=future)

    def finalize(self):
        """ Set the cubegen outputs as the WC outputs  """

        if not self._check_if_previous_calc_ok(self.ctx.cubegen_node):
            return self.exit_codes.ERROR_TERMINATION  # pylint: disable=no-member

        self.report("Setting outputs")
        for cubegen_out in list(self.ctx.cubegen_node.outputs):
            self.out(cubegen_out, self.ctx.cubegen_node.outputs[cubegen_out])
