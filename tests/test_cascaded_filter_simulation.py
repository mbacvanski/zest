#!/usr/bin/env python3
import unittest
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, SubCircuit
from zest.simulation import check_simulation_requirements
from tests.waveform_test_framework import WaveformTestMixin
from tests.golden_test_framework import GoldenTestMixin
from tests.simple_test_helpers import (
    create_rc_stage_definition, 
    create_rc_stage_with_custom_resistor_definition,
    create_voltage_divider_with_custom_resistors_definition
)

class TestCascadedFilterSimulation(WaveformTestMixin, GoldenTestMixin, unittest.TestCase):
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
        
        # 3.5. Set initial conditions for proper transient behavior
        # Capacitors should start uncharged (0V) for step response
        main_circuit.set_initial_condition(stage1.vout, 0.0)  # Stage 1 output starts at 0V
        main_circuit.set_initial_condition(stage2.vout, 0.0)  # Stage 2 output starts at 0V

        # 4. Run a transient simulation.
        # R=10k, C=1uF -> Time constant is 10ms. Simulate for longer to see full settling.
        end_time = 100e-3  # 100ms = 10 time constants for better settling
        results = main_circuit.simulate_transient(step_time=1e-5, end_time=end_time)
        self.assertIsNotNone(results)

        # 5. Extract and verify results.
        times = results.get_time_vector()
        if times is None and hasattr(results, 'time') and results.time is not None:
            times = results.time
        v_out_stage1 = results.get_node_voltage(stage1.vout)
        v_out_stage2 = results.get_node_voltage(stage2.vout)

        # Verification A: Initial conditions should be near 0V (capacitors uncharged)
        stage1_initial = v_out_stage1[0]
        stage2_initial = v_out_stage2[0]
        
        print(f"Initial conditions:")
        print(f"  Stage 1 starts at: {stage1_initial:.6f}V")
        print(f"  Stage 2 starts at: {stage2_initial:.6f}V")
        
        self.assertLess(abs(stage1_initial), 0.1, msg="Stage 1 should start near 0V (uncharged capacitor)")
        self.assertLess(abs(stage2_initial), 0.1, msg="Stage 2 should start near 0V (uncharged capacitor)")
        
        # Verification B: Final voltages should approach the 1V input
        stage1_final = v_out_stage1[-1]
        stage2_final = v_out_stage2[-1]
        
        print(f"Final voltages:")
        print(f"  Stage 1 ends at: {stage1_final:.6f}V")
        print(f"  Stage 2 ends at: {stage2_final:.6f}V")
        
        # After 100ms (10 time constants), should be very close to 1V
        self.assertGreater(stage1_final, 0.95, msg="Stage 1 should reach at least 95% of 1V after sufficient time")
        self.assertGreater(stage2_final, 0.9, msg="Stage 2 should reach at least 90% of 1V (slower due to cascading)")
        
        # Both should be reasonable fractions of the input
        self.assertLess(stage1_final, 1.05, msg="Stage 1 shouldn't exceed input voltage significantly")
        self.assertLess(stage2_final, 1.05, msg="Stage 2 shouldn't exceed input voltage significantly")
        
        # Verification C: Analyze settling behavior - Stage 1 should settle faster than Stage 2
        print(f"Analyzing settling behavior at key time points:")
        
        tau = 10e-3  # Expected time constant: 10ms  
        test_times = [1*tau, 2*tau, 3*tau, 5*tau]  # 10ms, 20ms, 30ms, 50ms
        
        for test_time in test_times:
            # Find closest time point
            idx = np.argmin(np.abs(times - test_time))
            actual_time = times[idx]
            v1 = v_out_stage1[idx]
            v2 = v_out_stage2[idx]
            
            print(f"  At t={actual_time*1000:.1f}ms: Stage1={v1:.4f}V, Stage2={v2:.4f}V")
            
            # Stage 1 should be ahead of Stage 2 during settling (except at very end)
            if actual_time < 0.8 * times[-1]:  # Not in final settling region
                self.assertGreaterEqual(v1, v2, 
                    f"Stage 1 should settle faster than Stage 2 at t={actual_time*1000:.1f}ms")
        
        # Verification D: Check exponential-like behavior (monotonic increase)
        # Both voltages should be monotonically increasing (or at least non-decreasing)
        stage1_diffs = np.diff(v_out_stage1)
        stage2_diffs = np.diff(v_out_stage2)
        
        negative_changes_s1 = np.sum(stage1_diffs < -0.001)  # Allow small numerical noise
        negative_changes_s2 = np.sum(stage2_diffs < -0.001)
        
        print(f"Monotonicity check:")
        print(f"  Stage 1 negative changes: {negative_changes_s1}")
        print(f"  Stage 2 negative changes: {negative_changes_s2}")
        
        # Should have very few (ideally zero) significant negative changes
        self.assertLess(negative_changes_s1, len(times) * 0.01, 
                       "Stage 1 should show monotonic increasing behavior")
        self.assertLess(negative_changes_s2, len(times) * 0.01, 
                       "Stage 2 should show monotonic increasing behavior")

        # Verification B: Compare waveform against a golden file.
        self.assert_waveform_matches_golden(
            "cascaded_rc_filter.csv",
            times,
            [v_out_stage1, v_out_stage2],
            ('V(stage1_out)', 'V(stage2_out)')
        )
        
        # Verification C: Generate plots for visual inspection
        print(f"Generating plots with {len(times)} time points...")
        print(f"Time range: {times[0]*1000:.1f} to {times[-1]*1000:.1f} ms")
        print(f"Stage 1: {v_out_stage1[0]:.4f}V → {v_out_stage1[-1]:.4f}V")
        print(f"Stage 2: {v_out_stage2[0]:.4f}V → {v_out_stage2[-1]:.4f}V")
        print(f"✅ Proper RC step response with initial conditions applied")
        print(f"✅ Both stages show exponential settling from 0V to 1V")
        
        # Convert time to milliseconds for better readability
        times_ms = times * 1000
        v_input = np.ones_like(times)  # 1V step input
        
        # Create simple step response plot using existing framework
        self.plot_and_save_transient(
            times_ms,
            [v_out_stage1, v_out_stage2],
            value_names=('Stage 1 Output', 'Stage 2 Output'),
            title="Cascaded RC Filter Step Response",
            filename="cascaded_rc_filter_step_response.png"
        )
        
        # Create detailed comparison plot with input and analysis
        def create_detailed_plot():
            fig = plt.figure(figsize=(12, 8))
            
            plt.subplot(2, 1, 1)
            plt.plot(times_ms, v_input, 'k--', linewidth=2, label='Input (1V Step)')
            plt.plot(times_ms, v_out_stage1, 'b-', linewidth=2, label='Stage 1 Output (First RC)')
            plt.plot(times_ms, v_out_stage2, 'r-', linewidth=2, label='Stage 2 Output (Second RC)')
            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (V)')
            plt.title('Cascaded RC Filter Step Response - Proper Transient Behavior')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1.1)
            
            # Zoom in on the first 150ms to see the settling behavior  
            plt.subplot(2, 1, 2)
            mask = times_ms <= 150
            plt.plot(times_ms[mask], v_input[mask], 'k--', linewidth=2, label='Input')
            plt.plot(times_ms[mask], v_out_stage1[mask], 'b-', linewidth=2, label='Stage 1')
            plt.plot(times_ms[mask], v_out_stage2[mask], 'r-', linewidth=2, label='Stage 2')
            
            # Add time constant markers
            tau = 10  # 10ms time constant
            plt.axvline(tau, color='gray', linestyle=':', alpha=0.7, label='τ = 10ms')
            plt.axvline(3*tau, color='gray', linestyle=':', alpha=0.5, label='3τ (95%)')
            plt.axvline(5*tau, color='gray', linestyle=':', alpha=0.3, label='5τ (99%)')
            
            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (V)')
            plt.title('Cascaded RC Filter - First 150ms (Stage 2 Lags Behind Stage 1)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1.1)
            
            plt.tight_layout()
            return fig
        
        # Use unified plotting method
        self.create_and_show_plot(
            create_detailed_plot, 
            "cascaded_rc_filter_detailed.png",
            "Cascaded RC Filter Detailed Analysis"
        )

    def test_mixed_normal_and_custom_resistor_stages(self):
        """
        Tests a cascaded filter where Stage 1 uses normal resistor and Stage 2 uses custom resistor.
        Verifies that custom resistor from include file works identically to normal resistor.
        """
        # 1. Get stage definitions - mix normal and custom
        normal_stage_def = create_rc_stage_definition()
        custom_stage_def = create_rc_stage_with_custom_resistor_definition()

        # 2. Build the main circuit
        main_circuit = Circuit("Mixed_Cascaded_RC_Filter")
        v_in = VoltageSource(voltage=1.0)

        # Stage 1: normal resistor, Stage 2: custom resistor
        stage1 = SubCircuit(definition=normal_stage_def, name="X_Stage1_Normal")
        stage2 = SubCircuit(definition=custom_stage_def, name="X_Stage2_Custom")
        
        main_circuit.add_component(v_in)
        main_circuit.add_component(stage1)
        main_circuit.add_component(stage2)

        # 3. Wire the circuit
        main_circuit.wire(v_in.neg, main_circuit.gnd)
        main_circuit.wire(stage1.gnd, main_circuit.gnd)
        main_circuit.wire(stage2.gnd, main_circuit.gnd)
        main_circuit.wire(v_in.pos, stage1.vin)
        main_circuit.wire(stage1.vout, stage2.vin)
        
        # Set initial conditions
        main_circuit.set_initial_condition(stage1.vout, 0.0)
        main_circuit.set_initial_condition(stage2.vout, 0.0)

        # 4. Check netlist includes are handled correctly
        netlist = main_circuit.compile_to_spice()
        print(f"\n=== Mixed Normal/Custom Resistor Netlist ===")
        print(netlist)
        
        # Golden file test - ensure netlist structure remains consistent
        self.assert_circuit_matches_golden(main_circuit, "mixed_normal_custom_resistor_stages.spice")
        
        # Verify include statement is present and not duplicated
        include_lines = [line for line in netlist.split('\n') if '.INCLUDE' in line.upper()]
        self.assertEqual(len(include_lines), 1, "Should have exactly one .INCLUDE statement")
        self.assertIn("custom_resistor.lib", include_lines[0], "Should include custom resistor library")
        
        # Verify both subcircuit definitions are present
        self.assertIn(".SUBCKT RC_FILTER_STAGE", netlist, "Normal RC stage should be defined")
        self.assertIn(".SUBCKT RC_FILTER_STAGE_CUSTOM", netlist, "Custom RC stage should be defined")

        # 5. Run simulation
        results = main_circuit.simulate_transient(step_time=1e-5, end_time=100e-3)
        self.assertIsNotNone(results)

        times = results.get_time_vector()
        if times is None and hasattr(results, 'time') and results.time is not None:
            times = results.time
        v_out_stage1 = results.get_node_voltage(stage1.vout)
        v_out_stage2 = results.get_node_voltage(stage2.vout)

        # 6. Verify behavior is similar to normal cascaded filter
        print(f"\nMixed resistor results:")
        print(f"  Stage 1 (normal): {v_out_stage1[0]:.6f}V → {v_out_stage1[-1]:.6f}V")
        print(f"  Stage 2 (custom): {v_out_stage2[0]:.6f}V → {v_out_stage2[-1]:.6f}V")
        
        # Initial conditions check
        self.assertLess(abs(v_out_stage1[0]), 0.1, "Stage 1 should start near 0V")
        self.assertLess(abs(v_out_stage2[0]), 0.1, "Stage 2 should start near 0V")
        
        # Final values should be reasonable (both resistors are 10kΩ so behavior should be identical)
        self.assertGreater(v_out_stage1[-1], 0.95, "Stage 1 should reach at least 95% of 1V")
        self.assertGreater(v_out_stage2[-1], 0.9, "Stage 2 should reach at least 90% of 1V")
        
        # Stage 1 should settle faster than Stage 2 (cascading effect)
        mid_idx = len(times) // 2
        self.assertGreaterEqual(v_out_stage1[mid_idx], v_out_stage2[mid_idx], 
                               "Stage 1 should settle faster than Stage 2")
        
        # Generate comparison plot for mixed resistor types
        def create_mixed_resistor_plot():
            times_ms = times * 1000
            fig = plt.figure(figsize=(10, 6))
            
            plt.plot(times_ms, v_out_stage1, 'b-', linewidth=2, label='Stage 1 (Normal Resistor)')
            plt.plot(times_ms, v_out_stage2, 'r-', linewidth=2, label='Stage 2 (Custom Resistor)')
            plt.axhline(y=1.0, color='k', linestyle='--', alpha=0.5, label='Target (1V)')
            
            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (V)')
            plt.title('Mixed Normal/Custom Resistor Stages Comparison')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1.1)
            
            return fig
        
        self.create_and_show_plot(
            create_mixed_resistor_plot, 
            "mixed_normal_custom_resistor_comparison.png",
            "Mixed Resistor Types Comparison"
        )

    def test_both_stages_use_custom_resistors(self):
        """
        Tests a cascaded filter where both stages use custom resistors from include file.
        Verifies include file deduplication and equivalent behavior to normal resistors.
        """
        # 1. Get custom stage definition for both stages
        custom_stage_def = create_rc_stage_with_custom_resistor_definition()

        # 2. Build the main circuit - both stages use custom resistors
        main_circuit = Circuit("Double_Custom_Cascaded_RC_Filter")
        v_in = VoltageSource(voltage=1.0)

        stage1 = SubCircuit(definition=custom_stage_def, name="X_Stage1_Custom")
        stage2 = SubCircuit(definition=custom_stage_def, name="X_Stage2_Custom")
        
        main_circuit.add_component(v_in)
        main_circuit.add_component(stage1)
        main_circuit.add_component(stage2)

        # 3. Wire the circuit
        main_circuit.wire(v_in.neg, main_circuit.gnd)
        main_circuit.wire(stage1.gnd, main_circuit.gnd)
        main_circuit.wire(stage2.gnd, main_circuit.gnd)
        main_circuit.wire(v_in.pos, stage1.vin)
        main_circuit.wire(stage1.vout, stage2.vin)
        
        # Set initial conditions
        main_circuit.set_initial_condition(stage1.vout, 0.0)
        main_circuit.set_initial_condition(stage2.vout, 0.0)

        # 4. Check netlist includes are properly deduplicated
        netlist = main_circuit.compile_to_spice()
        print(f"\n=== Both Custom Resistors Netlist ===")
        print(netlist)
        
        # Golden file test - ensure netlist structure with deduplication remains consistent
        self.assert_circuit_matches_golden(main_circuit, "both_stages_custom_resistors.spice")
        
        # Verify include statement is present only once (no duplication)
        include_lines = [line for line in netlist.split('\n') if '.INCLUDE' in line.upper()]
        self.assertEqual(len(include_lines), 1, "Should have exactly one .INCLUDE statement (deduplicated)")
        self.assertIn("custom_resistor.lib", include_lines[0], "Should include custom resistor library")
        
        # Verify custom subcircuit definition appears only once (deduplicated)
        custom_subckt_count = netlist.count(".SUBCKT RC_FILTER_STAGE_CUSTOM")
        self.assertEqual(custom_subckt_count, 1, "Custom subcircuit definition should appear only once")
        
        # Verify both instances are instantiated (look for full instance lines)
        netlist_lines = netlist.split('\n')
        stage1_instances = [line for line in netlist_lines if line.strip().startswith("XX_Stage1_Custom ")]
        stage2_instances = [line for line in netlist_lines if line.strip().startswith("XX_Stage2_Custom ")]
        
        self.assertEqual(len(stage1_instances), 1, f"Stage 1 should be instantiated once, found: {stage1_instances}")
        self.assertEqual(len(stage2_instances), 1, f"Stage 2 should be instantiated once, found: {stage2_instances}")

        # 5. Run simulation
        results = main_circuit.simulate_transient(step_time=1e-5, end_time=100e-3)
        self.assertIsNotNone(results)

        times = results.get_time_vector()
        if times is None and hasattr(results, 'time') and results.time is not None:
            times = results.time
        v_out_stage1 = results.get_node_voltage(stage1.vout)
        v_out_stage2 = results.get_node_voltage(stage2.vout)

        # 6. Verify behavior is equivalent to normal resistor version
        print(f"\nDouble custom resistor results:")
        print(f"  Stage 1 (custom): {v_out_stage1[0]:.6f}V → {v_out_stage1[-1]:.6f}V")
        print(f"  Stage 2 (custom): {v_out_stage2[0]:.6f}V → {v_out_stage2[-1]:.6f}V")
        
        # Initial conditions check
        self.assertLess(abs(v_out_stage1[0]), 0.1, "Stage 1 should start near 0V")
        self.assertLess(abs(v_out_stage2[0]), 0.1, "Stage 2 should start near 0V")
        
        # Final values should be equivalent to normal resistor behavior
        self.assertGreater(v_out_stage1[-1], 0.95, "Stage 1 should reach at least 95% of 1V")
        self.assertGreater(v_out_stage2[-1], 0.9, "Stage 2 should reach at least 90% of 1V")
        
        # Cascading behavior should be identical
        tau = 10e-3  # Time constant should be same (10kΩ × 1μF = 10ms)
        test_times = [1*tau, 2*tau, 3*tau]
        
        print(f"Cascading behavior verification:")
        for test_time in test_times:
            idx = np.argmin(np.abs(times - test_time))
            v1 = v_out_stage1[idx]
            v2 = v_out_stage2[idx]
            print(f"  At t={times[idx]*1000:.1f}ms: Stage1={v1:.4f}V, Stage2={v2:.4f}V")
            
            # Stage 1 should be ahead of Stage 2 during settling
            if times[idx] < 0.8 * times[-1]:
                self.assertGreaterEqual(v1, v2, 
                    f"Stage 1 should settle faster than Stage 2 at t={times[idx]*1000:.1f}ms")

        # 7. Compare against baseline normal resistor test
        # Run equivalent circuit with normal resistors for comparison
        normal_stage_def = create_rc_stage_definition()
        baseline_circuit = Circuit("Baseline_Normal_Cascaded_RC_Filter")
        v_in_baseline = VoltageSource(voltage=1.0)
        
        stage1_baseline = SubCircuit(definition=normal_stage_def, name="X_Stage1_Baseline")
        stage2_baseline = SubCircuit(definition=normal_stage_def, name="X_Stage2_Baseline")
        
        baseline_circuit.add_component(v_in_baseline)
        baseline_circuit.add_component(stage1_baseline)
        baseline_circuit.add_component(stage2_baseline)
        
        baseline_circuit.wire(v_in_baseline.neg, baseline_circuit.gnd)
        baseline_circuit.wire(stage1_baseline.gnd, baseline_circuit.gnd)
        baseline_circuit.wire(stage2_baseline.gnd, baseline_circuit.gnd)
        baseline_circuit.wire(v_in_baseline.pos, stage1_baseline.vin)
        baseline_circuit.wire(stage1_baseline.vout, stage2_baseline.vin)
        
        baseline_circuit.set_initial_condition(stage1_baseline.vout, 0.0)
        baseline_circuit.set_initial_condition(stage2_baseline.vout, 0.0)
        
        baseline_results = baseline_circuit.simulate_transient(step_time=1e-5, end_time=100e-3)
        baseline_times = baseline_results.get_time_vector()
        if baseline_times is None and hasattr(baseline_results, 'time') and baseline_results.time is not None:
            baseline_times = baseline_results.time
        baseline_v1 = baseline_results.get_node_voltage(stage1_baseline.vout)
        baseline_v2 = baseline_results.get_node_voltage(stage2_baseline.vout)
        
        # Compare final values (should be very close)
        final_diff_s1 = abs(v_out_stage1[-1] - baseline_v1[-1])
        final_diff_s2 = abs(v_out_stage2[-1] - baseline_v2[-1])
        
        print(f"\nComparison with normal resistor baseline:")
        print(f"  Stage 1 difference: {final_diff_s1:.6f}V")
        print(f"  Stage 2 difference: {final_diff_s2:.6f}V")
        
        self.assertLess(final_diff_s1, 0.01, "Custom resistor Stage 1 should behave like normal resistor")
        self.assertLess(final_diff_s2, 0.01, "Custom resistor Stage 2 should behave like normal resistor")
        
        print(f"✅ Custom resistors behave identically to normal resistors")
        print(f"✅ Include file deduplication working correctly")

    def test_different_subcircuits_same_include_deduplication(self):
        """
        Tests that when two different subcircuit types both use the same include file,
        the include statement appears only once in the top-level netlist.
        Uses RC filter and voltage divider subcircuits, both using custom_resistor.lib.
        """
        # 1. Get two different subcircuit types that both use custom resistors
        rc_filter_def = create_rc_stage_with_custom_resistor_definition()
        voltage_divider_def = create_voltage_divider_with_custom_resistors_definition()

        # 2. Build the main circuit using both subcircuit types
        main_circuit = Circuit("Mixed_Subcircuit_Types_Test")
        v_in = VoltageSource(voltage=5.0)  # 5V input

        # Create instances of both subcircuit types
        rc_stage = SubCircuit(definition=rc_filter_def, name="X_RC_Filter")
        divider_stage = SubCircuit(definition=voltage_divider_def, name="X_Voltage_Divider")
        
        main_circuit.add_component(v_in)
        main_circuit.add_component(rc_stage)
        main_circuit.add_component(divider_stage)

        # 3. Wire the circuit - RC filter cascaded with voltage divider
        main_circuit.wire(v_in.neg, main_circuit.gnd)
        main_circuit.wire(rc_stage.gnd, main_circuit.gnd)
        main_circuit.wire(divider_stage.gnd, main_circuit.gnd)
        
        # Input to RC filter
        main_circuit.wire(v_in.pos, rc_stage.vin)
        
        # RC filter output to voltage divider input
        main_circuit.wire(rc_stage.vout, divider_stage.vin)
        
        # Set initial conditions
        main_circuit.set_initial_condition(rc_stage.vout, 0.0)
        main_circuit.set_initial_condition(divider_stage.vout, 0.0)

        # 4. Check netlist includes are properly deduplicated across different subcircuit types
        netlist = main_circuit.compile_to_spice()
        print(f"\n=== Different Subcircuits Same Include Netlist ===")
        print(netlist)
        
        # Golden file test - ensure netlist structure with cross-subcircuit deduplication remains consistent
        self.assert_circuit_matches_golden(main_circuit, "different_subcircuits_same_include.spice")
        
        # Critical test: Only one .INCLUDE statement should exist despite two different subcircuit types
        include_lines = [line for line in netlist.split('\n') if '.INCLUDE' in line.upper()]
        self.assertEqual(len(include_lines), 1, 
                        "Should have exactly one .INCLUDE statement even with different subcircuit types")
        self.assertIn("custom_resistor.lib", include_lines[0], 
                     "Should include custom resistor library")
        
        # Verify both subcircuit definitions are present
        self.assertIn(".SUBCKT RC_FILTER_STAGE_CUSTOM", netlist, 
                     "RC filter subcircuit should be defined")
        self.assertIn(".SUBCKT VOLTAGE_DIVIDER_CUSTOM", netlist, 
                     "Voltage divider subcircuit should be defined")
        
        # Verify both subcircuit instances are present
        self.assertIn("XX_RC_Filter ", netlist, "RC filter instance should be present")
        self.assertIn("XX_Voltage_Divider ", netlist, "Voltage divider instance should be present")
        
        # Count subcircuit definitions to ensure no duplication
        rc_subckt_count = netlist.count(".SUBCKT RC_FILTER_STAGE_CUSTOM")
        divider_subckt_count = netlist.count(".SUBCKT VOLTAGE_DIVIDER_CUSTOM")
        
        self.assertEqual(rc_subckt_count, 1, "RC filter subcircuit should be defined exactly once")
        self.assertEqual(divider_subckt_count, 1, "Voltage divider subcircuit should be defined exactly once")

        # 5. Run simulation to verify electrical behavior
        results = main_circuit.simulate_transient(step_time=1e-5, end_time=50e-3)
        self.assertIsNotNone(results)

        times = results.get_time_vector()
        if times is None and hasattr(results, 'time') and results.time is not None:
            times = results.time
        v_rc_out = results.get_node_voltage(rc_stage.vout)
        v_divider_out = results.get_node_voltage(divider_stage.vout)

        # 6. Verify cascaded behavior with different subcircuit types
        print(f"\nMixed subcircuit types simulation results:")
        print(f"  RC filter: {v_rc_out[0]:.6f}V → {v_rc_out[-1]:.6f}V")
        print(f"  Voltage divider: {v_divider_out[0]:.6f}V → {v_divider_out[-1]:.6f}V")
        
        # Initial conditions check
        self.assertLess(abs(v_rc_out[0]), 0.1, "RC filter should start near 0V")
        self.assertLess(abs(v_divider_out[0]), 0.1, "Voltage divider should start near 0V")
        
        # RC filter should settle towards input voltage (5V), but limited by voltage divider loading
        # The voltage divider (2×10kΩ = 20kΩ total) loads the RC filter's 10kΩ resistor
        # This creates a voltage divider effect: Vout = 5V × (20kΩ)/(10kΩ+20kΩ) = 5V × 2/3 ≈ 3.33V
        expected_rc_out = 5.0 * (20.0 / 30.0)  # 5V × (20kΩ)/(10kΩ+20kΩ) = 3.33V
        print(f"  Expected RC output (with loading): {expected_rc_out:.6f}V")
        
        self.assertGreater(v_rc_out[-1], 3.0, "RC filter should reach at least 60% of 5V (accounting for loading)")
        self.assertLess(abs(v_rc_out[-1] - expected_rc_out), 0.5, "RC filter should settle near expected loaded voltage")
        
        # Voltage divider should settle to half the RC output (R1=R2=10kΩ, so 50% division)
        expected_divider_out = v_rc_out[-1] / 2.0  # 50% voltage division
        actual_divider_out = v_divider_out[-1]
        divider_error = abs(actual_divider_out - expected_divider_out)
        
        print(f"  Expected divider output: {expected_divider_out:.6f}V")
        print(f"  Actual divider output: {actual_divider_out:.6f}V")
        print(f"  Divider error: {divider_error:.6f}V")
        
        self.assertLess(divider_error, 0.1, "Voltage divider should output ~50% of RC filter output")
        
        # Verify cascading: divider output should be less than RC output
        self.assertLess(v_divider_out[-1], v_rc_out[-1], 
                       "Voltage divider output should be less than RC filter output")
        
        print(f"✅ Two different subcircuit types both using custom resistors")
        print(f"✅ Include file deduplicated correctly across subcircuit types")
        print(f"✅ RC filter → Voltage divider cascading works correctly")
        
        # Generate plot showing different subcircuit types working together
        def create_mixed_subcircuits_plot():
            times_ms = times * 1000
            v_input = np.full_like(times, 5.0)  # 5V input
            
            fig = plt.figure(figsize=(12, 8))
            
            # Main plot showing all signals
            plt.subplot(2, 1, 1)
            plt.plot(times_ms, v_input, 'k--', linewidth=2, label='Input (5V)')
            plt.plot(times_ms, v_rc_out, 'b-', linewidth=2, label='RC Filter Output')
            plt.plot(times_ms, v_divider_out, 'r-', linewidth=2, label='Voltage Divider Output')
            plt.axhline(y=expected_rc_out, color='b', linestyle=':', alpha=0.7, 
                       label=f'Expected RC Out ({expected_rc_out:.2f}V)')
            
            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (V)')
            plt.title('Different Subcircuit Types Using Same Include File')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 5.5)
            
            # Zoomed view of settling behavior
            plt.subplot(2, 1, 2)
            mask = times_ms <= 100  # First 100ms
            plt.plot(times_ms[mask], v_rc_out[mask], 'b-', linewidth=2, label='RC Filter (Custom R + C)')
            plt.plot(times_ms[mask], v_divider_out[mask], 'r-', linewidth=2, label='Voltage Divider (2× Custom R)')
            
            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (V)')
            plt.title('RC Filter → Voltage Divider Cascading (First 100ms)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
        
        self.create_and_show_plot(
            create_mixed_subcircuits_plot, 
            "different_subcircuits_same_include.png",
            "Different Subcircuit Types with Same Include"
        )


if __name__ == '__main__':
    unittest.main() 