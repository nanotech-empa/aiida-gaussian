import io
import ase

import numpy as np

from aiida.engine import WorkChain, ToContext
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

        spec.input('gaussian_calc_folder',
                   valid_type=RemoteData,
                   required=True,
                   help='The gaussian calculation output folder.')

        spec.input('gaussian_output_params',
                   valid_type=Dict,
                   required=True,
                   help='The gaussian calculation output parameters.')

        spec.input('n_occ',
                   valid_type=Int,
                   required=False,
                   default=lambda: Int(1),
                   help='Number of occupied orbital cubes to generate')

        spec.input('n_virt',
                   valid_type=Int,
                   required=False,
                   default=lambda: Int(1),
                   help='Number of virtual orbital cubes to generate')

        spec.input(
            'edge_space',
            valid_type=Float,
            required=False,
            default=lambda: Float(3.0),
            help='Extra cube space in addition to molecule bounding box [ang].'
        )

        spec.input('dx',
                   valid_type=Float,
                   required=False,
                   default=lambda: Float(0.15),
                   help='Cube file spacing [ang].')

        spec.input('retrieve_cubes',
                   valid_type=Bool,
                   required=False,
                   default=lambda: Bool(False),
                   help='should the cubes be retrieved?')

        spec.input(
            "cubegen_parser_name",
            valid_type=str,
            default=CubegenCalculation._DEFAULT_PARSER,
            non_db=True,
        )

        spec.input("cubegen_parser_params",
                   valid_type=Dict,
                   required=False,
                   default=lambda: Dict(dict={}),
                   help='Additional parameters to cubegen parser.')

        spec.outline(cls.formchk_step, cls.cubegen_step, cls.finalize)

        spec.outputs.dynamic = True

    def formchk_step(self):

        self.report("Running FormChk")

        builder = FormchkCalculation.get_builder()

        builder.parent_calc_folder = self.inputs.gaussian_calc_folder
        builder.code = self.inputs.formchk_code

        builder.metadata.options.resources = {
            "tot_num_mpiprocs": 1,
            "num_machines": 1,
        }

        builder.metadata.options.max_wallclock_seconds = 1 * 10 * 60

        future = self.submit(builder)
        return ToContext(formchk_node=future)

    def cubegen_step(self):

        self.report("Running Cubegen")

        gout_params = self.inputs.gaussian_output_params

        # --------------------------------------------------------------
        # Create the stencil

        ase_atoms = ase.Atoms(gout_params['atomnos'],
                              positions=gout_params['atomcoords'][0])

        xmin = np.min(ase_atoms.positions[:, 0]) - self.inputs.edge_space.value
        xmax = np.max(ase_atoms.positions[:, 0]) + self.inputs.edge_space.value
        ymin = np.min(ase_atoms.positions[:, 1]) - self.inputs.edge_space.value
        ymax = np.max(ase_atoms.positions[:, 1]) + self.inputs.edge_space.value
        zmin = np.min(ase_atoms.positions[:, 2]) - self.inputs.edge_space.value
        zmax = np.max(ase_atoms.positions[:, 2]) + self.inputs.edge_space.value

        geom_center = np.array([xmin + xmax, ymin + ymax, zmin + zmax]) / 2.0

        cell = np.array([xmax - xmin, ymax - ymin, zmax - zmin])

        cell_n = (np.round(cell / self.inputs.dx.value)).astype(int)

        stencil = b"-1 %f %f %f\n" % tuple(geom_center - cell / 2)
        stencil += b"%d %f 0.0 0.0\n" % (cell_n[0], self.inputs.dx.value)
        stencil += b"%d 0.0 %f 0.0\n" % (cell_n[1], self.inputs.dx.value)
        stencil += b"%d 0.0 0.0 %f\n" % (cell_n[2], self.inputs.dx.value)

        # --------------------------------------------------------------

        builder = CubegenCalculation.get_builder()
        builder.parent_calc_folder = self.ctx.formchk_node.outputs.remote_folder
        builder.code = self.inputs.cubegen_code

        # in the output params, orbital counting starts from 0
        homos = gout_params['homos']

        # use the cubegen convention, where counting starts from 1
        homos = [h + 1 for h in homos]

        # Generate same orbitals for both spin channels (in case of inequal spin populations,
        # choose such that both spin channels have at least n_occ occupied and n_virt unoccupied cubes)
        i_mo_start = max(min(homos) - self.inputs.n_occ.value + 1, 1)
        i_mo_end = max(homos) + self.inputs.n_virt.value

        params_dict = {
            "density": {
                "kind": "Density=SCF",
                "npts": -1,
            },
        }

        for i_mo in range(i_mo_start, i_mo_end + 1, 1):

            for i_spin, h in enumerate(homos):

                i_mo_wrt_homo = i_mo - h
                if i_mo_wrt_homo < 0:
                    label = "homo%+d" % i_mo_wrt_homo
                elif i_mo_wrt_homo == 0:
                    label = "homo"
                elif i_mo_wrt_homo == 1:
                    label = "lumo"
                elif i_mo_wrt_homo > 1:
                    label = "lumo%+d" % (i_mo_wrt_homo - 1)

                if len(homos) == 1:

                    params_dict["%d_%s" % (i_mo, label)] = {
                        "kind": "MO=%d" % i_mo,
                        "npts": -1,
                    }

                else:

                    spin_letter = "a" if i_spin == 0 else "b"

                    params_dict["%d_%s_%s" % (i_mo, spin_letter, label)] = {
                        "kind": "%sMO=%d" % (spin_letter.upper(), i_mo),
                        "npts": -1,
                    }

        if len(homos) == 2:
            params_dict['spin'] = {
                "kind": "Spin=SCF",
                "npts": -1,
            }

        builder.stencil = SinglefileData(io.BytesIO(stencil))
        builder.parameters = Dict(dict=params_dict)
        builder.retrieve_cubes = self.inputs.retrieve_cubes

        builder.parser_params = self.inputs.cubegen_parser_params

        builder.metadata.options.resources = {
            "tot_num_mpiprocs": 1,
            "num_machines": 1,
        }

        builder.metadata.options.max_wallclock_seconds = 1 * 60 * 60

        builder.metadata.options.parser_name = self.inputs.cubegen_parser_name

        future = self.submit(builder)
        return ToContext(cubegen_node=future)

    def finalize(self):
        """ Set the cubegen outputs as the WC outputs  """
        self.report("Setting outputs")
        for cubegen_out in list(self.ctx.cubegen_node.outputs):
            self.out(cubegen_out, self.ctx.cubegen_node.outputs[cubegen_out])
