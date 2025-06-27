#!/usr/bin/env python3
import unittest
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, SubCircuit
from zest.simulation import check_simulation_requirements
from tests.waveform_test_framework import WaveformTestMixin
from tests.simple_test_helpers import create_rc_stage_definition

class TestCascadedFilterSimulation(WaveformTestMixin, unittest.TestCase):
    """
    End-to-end test for a simple cascaded subcircuit simulation.
    """
    def setUp(self):
        super().setUp()
        self.available, self.message = check_simulation_requirements()
        if not self.available:
            self.skipTest(f"PySpice not available: {self.message}")

    def test_cascaded_rc_filter_step_response(self):
        """
        Tests the step response of a two-stage cascaded RC filter
        built from two instances of an RC filter subcircuit.
        """
        # 1. Get the subcircuit definition for one RC stage.
        rc_stage_def = create_rc_stage_definition()

        # 2. Build the main circuit.
        main_circuit = Circuit("Cascaded_RC_Filter")
        v_in = VoltageSource(voltage=1.0) # 1V step input

        # Instantiate the RC stage twice
        stage1 = SubCircuit(definition=rc_stage_def, name="X_Stage1")
        stage2 = SubCircuit(definition=rc_stage_def, name="X_Stage2")
        
        # Explicitly add components to the main circuit
        main_circuit.add_component(v_in)
        main_circuit.add_component(stage1)
        main_circuit.add_component(stage2)

        # 3. Wire the main circuit.
        main_circuit.wire(v_in.neg, main_circuit.gnd)
        main_circuit.wire(stage1.gnd, main_circuit.gnd)
        main_circuit.wire(stage2.gnd, main_circuit.gnd)

        # Connect source to the input of the first stage
        main_circuit.wire(v_in.pos, stage1.vin)

        # Connect the output of the first stage to the input of the second
        main_circuit.wire(stage1.vout, stage2.vin)

        # 4. Run a transient simulation.
        # R=10k, C=1uF -> Time constant is 10ms. Simulate for 50ms.
        end_time = 50e-3
        results = main_circuit.simulate_transient(step_time=1e-5, end_time=end_time)
        self.assertIsNotNone(results)

        # 5. Extract and verify results.
        times = results._extract_value(results.pyspice_results.time)
        v_out_stage1 = results.get_node_voltage(stage1.vout)
        v_out_stage2 = results.get_node_voltage(stage2.vout)

        # Verification A: Final voltage should approach the 1V input.
        final_voltage = v_out_stage2[-1]
        self.assertAlmostEqual(1.0, final_voltage, delta=0.05, msg="Final output voltage should be close to 1V.")

        # Verification B: Compare waveform against a golden file.
        self.assert_waveform_matches_golden(
            "cascaded_rc_filter.csv",
            times,
            [v_out_stage1, v_out_stage2],
            ('V(stage1_out)', 'V(stage2_out)')
        ) 