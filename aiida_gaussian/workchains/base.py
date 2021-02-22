# -*- coding: utf-8 -*-
"""Base work chain to run a CP2K calculation."""

import os
import sys

from typing import Optional

from aiida.common import AttributeDict

from aiida.engine import WorkChain, ToContext, process_handler, ProcessHandlerReport
from aiida.engine import BaseRestartWorkChain, while_
from aiida.orm import Int, Float, Str, Bool, Code, Dict, List
from aiida.orm import SinglefileData, StructureData, RemoteData
from aiida.orm import CalcJobNode

from aiida.plugins import CalculationFactory

GaussianCalculation = CalculationFactory('gaussian')


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

        spec.expose_outputs(GaussianCalculation)

        # TODO: Is there any way to expose dynamic outputs?
        #spec.outputs.dynamic = True

        spec.exit_code(
            350,
            'ERROR_UNRECOVERABLE_SCF_FAILURE',
            message=
            'The calculation failed with an unrecoverable SCF convergence error.'
        )

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.
        
        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """
        super(GaussianBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(
            self.exposed_inputs(GaussianCalculation, 'gaussian'))

    @process_handler(
        priority=400,
        exit_codes=[GaussianCalculation.exit_codes.ERROR_SCF_FAILURE])
    def handle_scf_failure(self, calculation):
        """
        Try to restart with
        1) scf=(qc)
        and if it doesn't work then
        2) scf=(yqc)
        """

        params = dict(self.ctx.inputs.parameters)
        route_params = params['route_parameters']

        if 'scf' not in route_params:
            route_params['scf'] = {}

        if 'yqc' in route_params['scf']:
            # QC and YQC failed:
            self.report("SCF failed with QC and YQC, giving up...")
            return ProcessHandlerReport(
                False, self.exit_codes.ERROR_UNRECOVERABLE_SCF_FAILURE)

        new_scf = {}
        # keep the user-set convergence criterion; replace rest
        if 'conver' in route_params['scf']:
            new_scf['conver'] = route_params['scf']['conver']

        if 'qc' in route_params['scf']:
            self.report("SCF=(QC) failed, retrying with SCF=(YQC)")
            new_scf['yqc'] = None
        else:
            self.report("SCF failed, retrying with SCF=(QC)")
            new_scf['qc'] = None

        # Update the params Dict
        route_params['scf'] = new_scf
        self.ctx.inputs.parameters = Dict(dict=params)

        return ProcessHandlerReport(False)
