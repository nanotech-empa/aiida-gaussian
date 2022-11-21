# -*- coding: utf-8 -*-
"""Base work chain to run a Gaussian calculation."""

from aiida.common import AttributeDict

from aiida.engine import process_handler, ProcessHandlerReport
from aiida.engine import BaseRestartWorkChain, while_
from aiida.orm import Dict

from aiida.plugins import CalculationFactory, DataFactory

GaussianCalculation = CalculationFactory('gaussian')
StructureData = DataFactory('core.structure')


class GaussianBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a Gaussian calculation with automated error handling and restarts."""

    _process_class = GaussianCalculation

    @classmethod
    def define(cls, spec):

        super(GaussianBaseWorkChain, cls).define(spec)
        spec.expose_inputs(GaussianCalculation, namespace='gaussian')

        spec.outline(
            cls.setup,
            while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )

        spec.outputs.dynamic = True

        spec.exit_code(
            350,
            'ERROR_UNRECOVERABLE_SCF_FAILURE',
            message='The calculation failed with an unrecoverable SCF convergence error.'
        )

        spec.exit_code(
            399,
            'ERROR_UNRECOVERABLE_TERMINATION',
            message='The calculation failed with an unrecoverable error.'
        )

    def setup(self):
        """Call the `setup` and create the inputs dictionary in `self.ctx.inputs`.
        
        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to
        submit the calculations in the internal loop.
        """
        super(GaussianBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(self.exposed_inputs(GaussianCalculation, 'gaussian'))

    @process_handler(
        priority=400,
        exit_codes=[
            GaussianCalculation.exit_codes.ERROR_SCF_FAILURE,
            GaussianCalculation.exit_codes.ERROR_INACCURATE_QUADRATURE_CALDSU
        ]
    )
    def handle_scf_failure(self, node):
        """
        Try to restart with
        1) scf=(yqc)
        and if it doesn't work then
        2) scf=(xqc)
        """

        params = dict(self.ctx.inputs.parameters)
        route_params = params['route_parameters']

        if 'scf' not in route_params:
            route_params['scf'] = {}

        if 'xqc' in route_params['scf']:
            # XQC and YQC failed:
            self.report("SCF failed with YQC and XQC, giving up...")
            return ProcessHandlerReport(True, self.exit_codes.ERROR_UNRECOVERABLE_SCF_FAILURE)  # pylint: disable=no-member

        new_scf = {}
        # keep the user-set convergence criterion; replace rest
        if 'conver' in route_params['scf']:
            new_scf['conver'] = route_params['scf']['conver']

        if 'yqc' in route_params['scf']:
            self.report("SCF=(YQC) failed, retrying with SCF=(XQC)")
            new_scf['xqc'] = None
        else:
            self.report("SCF failed, retrying with SCF=(YQC)")
            new_scf['yqc'] = None

        # Update the params Dict
        route_params['scf'] = new_scf
        self.ctx.inputs.parameters = Dict(params)

        return ProcessHandlerReport(True)

    @process_handler(
        priority=500, exit_codes=[GaussianCalculation.exit_codes.ERROR_ASYTOP], enabled=False
    )
    def handle_asytop_error(self, node):
        """Handle the error code 302 (ASYTOP)."""
        self.report(
            "ASYTOP error encountered. Rounding the coordinates to the 4th digit and trying again."
        )
        structure_ase = self.ctx.inputs.structure.get_ase()
        structure_ase.set_positions(structure_ase.get_positions().round(4))
        self.ctx.inputs.structure = StructureData(ase=structure_ase)
        return ProcessHandlerReport(True)

    @process_handler(
        priority=0, exit_codes=[GaussianCalculation.exit_codes.ERROR_NO_NORMAL_TERMINATION]
    )
    def handle_misc_failure(self, node):
        """
        By default, the BaseRestartWorkChain restarts any unhandled error once
        Disable this feature for the exit_code that corresponds to out-of-time
        """
        return ProcessHandlerReport(False, self.exit_codes.ERROR_UNRECOVERABLE_TERMINATION)  # pylint: disable=no-member

    def results(self):
        """Overload the method such that each dynamic output of GaussianCalculation is set."""
        node = self.ctx.children[self.ctx.iteration - 1]

        # We check the `is_finished` attribute of the work chain and not the successfulness of the last process
        # because the error handlers in the last iteration can have qualified a "failed" process as satisfactory
        # for the outcome of the work chain and so have marked it as `is_finished=True`.
        max_iterations = self.inputs.max_iterations.value  # type: ignore[union-attr]
        if not self.ctx.is_finished and self.ctx.iteration >= max_iterations:
            self.report(
                f'reached the maximum number of iterations {max_iterations}: '
                f'last ran {self.ctx.process_name}<{node.pk}>'
            )
            return self.exit_codes.ERROR_MAXIMUM_ITERATIONS_EXCEEDED  # pylint: disable=no-member

        self.report(f'The work chain completed after {self.ctx.iteration} iterations')

        self.out_many({key: node.outputs[key] for key in node.outputs})

        return None
