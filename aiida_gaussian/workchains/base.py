# -*- coding: utf-8 -*-
"""Base work chain to run a CP2K calculation."""

import os
import sys

from aiida.common import AttributeDict

from aiida.engine import WorkChain, ToContext
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

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.
        
        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """

        super(GaussianBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(
            self.exposed_inputs(GaussianCalculation, 'gaussian'))
