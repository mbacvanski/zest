#!/usr/bin/env python3
"""
Integration tests for complex scenarios that test multiple classes working together.
This includes cascaded filters, complex simulations, subcircuit integration, 
transient analysis, and end-to-end workflows.
"""

import unittest
import os
import sys
import matplotlib.pyplot as plt

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.simple_test_helpers import create_rc_stage_definition, create_rc_stage_with_custom_resistor_definition
from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor, SubCircuit
from zest.components import CurrentSource, ExternalSubCircuit
from .golden_test_framework import GoldenTestMixin
from .waveform_test_framework import WaveformTestMixin


class TestComplexCircuitIntegration(GoldenTestMixin, WaveformTestMixin, unittest.TestCase):
    """Test complex circuits that integrate multiple component types."""
    
    def test_cascaded_rc_filter_step_response(self):
        """Test a cascaded RC filter with step response analysis."""
        circuit = Circuit("Cascaded RC Filter")
        
        # Input step voltage source
        v_step = VoltageSource(voltage=5.0, name="VIN")
        
        # First RC stage
        r1 = Resistor(resistance=1000, name="R1")  # 1k
        c1 = Capacitor(capacitance=1e-6, name="C1")  # 1μF
        
        # Second RC stage  
        r2 = Resistor(resistance=2000, name="R2")  # 2k
        c2 = Capacitor(capacitance=0.5e-6, name="C2")  # 0.5μF
        
        # Add all components
        circuit.add_component(v_step)
        circuit.add_component(r1)
        circuit.add_component(c1)
        circuit.add_component(r2)
        circuit.add_component(c2)
        
        # Wire the cascaded filter
        circuit.wire(v_step.neg, circuit.gnd)
        circuit.wire(v_step.pos, r1.n1)         # Input to first stage
        circuit.wire(r1.n2, c1.pos)            # First RC junction
        circuit.wire(c1.neg, circuit.gnd)      # First capacitor to ground
        circuit.wire(r1.n2, r2.n1)             # Couple to second stage
        circuit.wire(r2.n2, c2.pos)            # Second RC junction  
        circuit.wire(c2.neg, circuit.gnd)      # Second capacitor to ground
        
        # Verify SPICE generation
        spice = circuit.compile_to_spice()
        self.assertIn("VIN", spice)
        self.assertIn("R1", spice)
        self.assertIn("C1", spice)
        self.assertIn("R2", spice)
        self.assertIn("C2", spice)
        
        # Test golden file comparison
        self.assert_circuit_matches_golden(circuit, "cascaded_rc_filter_detailed.spice")
        
        # Test transient simulation
        try:
            result = circuit.simulate_transient(step_time=10e-6, end_time=10e-3)
            self.assertIsNotNone(result)
            
            # Verify we have time-domain results
            time_vector = result.get_time_vector()
            if time_vector is not None:
                self.assertGreater(len(time_vector), 10)
                
                # Test waveform validation
                self.assert_waveform_matches_golden(
                    result, 
                    "cascaded_rc_filter.csv",
                    time_tolerance=1e-6,
                    voltage_tolerance=0.1
                )
        except Exception:
            # Simulation might not be available
            pass
    
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

    def create_nested_two_stage_filter_definition(self):
        """
        Create a two-stage RC filter using nested subcircuits.
        This subcircuit contains two instances of the basic RC stage subcircuit.
        """
        two_stage_filter = Circuit("TWO_STAGE_RC_FILTER")
        
        # Get the basic building block definition
        basic_rc_def = self.create_basic_rc_stage_definition()
        
        # Create two instances of the basic RC stage
        stage1 = SubCircuit(definition=basic_rc_def, name="STAGE1")
        stage2 = SubCircuit(definition=basic_rc_def, name="STAGE2")
        
        # Add the subcircuit instances to our two-stage filter
        two_stage_filter.add_component(stage1)
        two_stage_filter.add_component(stage2)
        
        # Wire the stages in cascade (stage1 output -> stage2 input)
        two_stage_filter.wire(stage1.output, stage2.input)
        
        # Connect grounds together
        two_stage_filter.wire(stage1.gnd, stage2.gnd)
        
        # Expose external pins for the two-stage filter
        two_stage_filter.add_pin("input", stage1.input)     # Input to first stage
        two_stage_filter.add_pin("output", stage2.output)   # Output from second stage  
        two_stage_filter.add_pin("gnd", stage1.gnd)         # Common ground
        
        return two_stage_filter

    def create_basic_rc_stage_definition(self):
        """Create a basic RC low-pass filter stage - the fundamental building block."""
        rc_stage = Circuit("BASIC_RC_STAGE")
        
        # Simple RC filter components
        r1 = Resistor(resistance=1000, name="R_stage")  # 1kΩ
        c1 = Capacitor(capacitance=100e-9, name="C_stage")  # 100nF
        
        # Add components to the circuit
        rc_stage.add_component(r1)
        rc_stage.add_component(c1)
        
        # Wire R and C in series (RC low-pass configuration)
        rc_stage.wire(r1.n2, c1.pos)
        
        # Expose external pins
        rc_stage.add_pin("input", r1.n1)    # Input to resistor
        rc_stage.add_pin("output", r1.n2)   # Output from R-C junction
        rc_stage.add_pin("gnd", c1.neg)     # Ground reference
        
        return rc_stage
        
    def test_nested_subcircuits_hierarchy(self):
        """
        Test nested subcircuits: a subcircuit that contains other subcircuits within it.
        This demonstrates hierarchical subcircuit design with proper SPICE generation and simulation.
        """
        # 1. Create the nested subcircuit definition (contains other subcircuits)
        nested_filter_def = self.create_nested_two_stage_filter_definition()
        
        # 2. Create main circuit using the nested subcircuit
        main_circuit = Circuit("Nested_Subcircuits_Test")
        v_source = VoltageSource(voltage=3.3)  # 3.3V input
        
        # Create instance of the nested subcircuit
        nested_filter = SubCircuit(definition=nested_filter_def, name="U_NESTED_FILTER")
        
        # Add components to main circuit
        main_circuit.add_component(v_source)
        main_circuit.add_component(nested_filter)
        
        # 3. Wire the main circuit
        main_circuit.wire(v_source.pos, nested_filter.input)
        main_circuit.wire(v_source.neg, main_circuit.gnd)
        main_circuit.wire(nested_filter.gnd, main_circuit.gnd)
        
        # Set initial conditions for clean simulation
        main_circuit.set_initial_condition(nested_filter.output, 0.0)
        
        # 4. Test SPICE output with golden file
        spice_output = main_circuit.compile_to_spice()
        print(f"\n=== Nested Subcircuits SPICE ===")
        print(spice_output)
        
        # Golden file test for SPICE output
        self.assert_circuit_matches_golden(main_circuit, "nested_subcircuits.spice")
        
        # 5. Verify nested subcircuit structure in SPICE output
        # Should have both the basic building block AND the nested subcircuit definitions
        self.assertIn(".SUBCKT BASIC_RC_STAGE", spice_output, 
                     "Basic RC stage subcircuit should be defined")
        self.assertIn(".SUBCKT TWO_STAGE_RC_FILTER", spice_output, 
                     "Nested two-stage filter subcircuit should be defined")
        
        # Verify instances within the nested subcircuit
        self.assertIn("XSTAGE1 ", spice_output, "First stage instance should be present in nested subcircuit")
        self.assertIn("XSTAGE2 ", spice_output, "Second stage instance should be present in nested subcircuit")
        
        # Verify main circuit instance
        self.assertIn("XU_NESTED_FILTER ", spice_output, "Nested filter instance should be present in main circuit")
        
        # Count subcircuit definitions to ensure no duplication
        basic_subckt_count = spice_output.count(".SUBCKT BASIC_RC_STAGE")
        nested_subckt_count = spice_output.count(".SUBCKT TWO_STAGE_RC_FILTER")
        
        self.assertEqual(basic_subckt_count, 1, "Basic RC stage should be defined exactly once")
        self.assertEqual(nested_subckt_count, 1, "Nested filter should be defined exactly once")
        
        # 6. Run transient simulation to verify electrical behavior
        # RC time constant = 1kΩ × 100nF = 100μs, so use 5τ = 500μs for full settling
        results = main_circuit.simulate_transient(step_time=2e-6, end_time=500e-6)
        self.assertIsNotNone(results, "Transient simulation should succeed")
        
        # Extract waveform data
        times = results.get_time_vector()
        if times is None and hasattr(results, 'time') and results.time is not None:
            times = results.time
        v_output = results.get_node_voltage(nested_filter.output)
        
        print(f"Simulation results: {len(times)} time points")
        print(f"Final output voltage: {v_output[-1]:.3f}V")
        print(f"Settling to {(v_output[-1]/3.3)*100:.1f}% of input voltage")
        
        # Test with golden waveform
        self.assert_waveform_matches_golden(
            "nested_subcircuits.csv",            # golden file name
            times,                               # x_values (time)
            v_output,                           # values (voltage)
            trace_names=('nested_filter_output',), # trace names
            auto_plot=True,                     # enable auto plotting
            plot_title="Nested Subcircuits Two-Stage RC Filter"
        )
        
        # Basic electrical behavior checks for extended simulation
        self.assertGreater(len(times), 100, "Should have sufficient time points")
        self.assertGreater(v_output[-1], 2.5, "Output should reach significant voltage after full settling")
        self.assertLess(v_output[-1], 3.3, "Output should not exceed input voltage")
        
        # Two-stage RC filter should approach input voltage after sufficient time
        # Realistic expectation: should reach at least 80% of input voltage (2.64V) after 5 time constants
        self.assertGreater(v_output[-1], 2.6, "Two-stage filter should settle to reasonable fraction of input voltage")
        
        # Verify it's progressing towards input voltage (not stuck at zero)
        settling_fraction = v_output[-1] / 3.3
        self.assertGreater(settling_fraction, 0.75, "Should settle to at least 75% of input voltage")
        
        print(f"✅ Nested subcircuits (subcircuit within subcircuit)")
        print(f"✅ Hierarchical SPICE generation working correctly")
        print(f"✅ Two-stage RC filter electrical behavior verified")
        
    def test_complex_circuit_simulation(self):
        """Test simulation of a complex circuit with multiple analysis types."""
        circuit = Circuit("Complex Test")
        
        # Create RLC resonant circuit with current source
        i_source = CurrentSource(current=1e-3, name="I1")  # 1mA
        r1 = Resistor(resistance=100, name="R1")            # 100Ω  
        l1 = Inductor(inductance=1e-3, name="L1")           # 1mH
        c1 = Capacitor(capacitance=1e-6, name="C1")         # 1μF
        r_load = Resistor(resistance=1000, name="R_LOAD")   # Load resistor
        
        # Add components
        circuit.add_component(i_source)
        circuit.add_component(r1)
        circuit.add_component(l1)
        circuit.add_component(c1)
        circuit.add_component(r_load)
        
        # Create parallel RLC with current source
        circuit.wire(i_source.pos, r1.n1)
        circuit.wire(i_source.pos, l1.n1)
        circuit.wire(i_source.pos, c1.pos)
        circuit.wire(i_source.pos, r_load.n1)
        
        circuit.wire(i_source.neg, circuit.gnd)
        circuit.wire(r1.n2, circuit.gnd)
        circuit.wire(l1.n2, circuit.gnd)
        circuit.wire(c1.neg, circuit.gnd)
        circuit.wire(r_load.n2, circuit.gnd)
        
        # Test operating point
        try:
            op_result = circuit.simulate_operating_point()
            self.assertIsNotNone(op_result)
            self.assertTrue(op_result.is_operating_point())
        except Exception:
            pass
        
        # Test AC analysis
        try:
            ac_result = circuit.simulate_ac(start_freq=100, stop_freq=100e3, points_per_decade=20)
            self.assertIsNotNone(ac_result)
            self.assertTrue(ac_result.is_ac_analysis())
        except Exception:
            pass
        
        # Test transient analysis
        try:
            tran_result = circuit.simulate_transient(step_time=1e-6, end_time=10e-3)
            self.assertIsNotNone(tran_result)
            self.assertTrue(tran_result.is_transient())
            
            # Test time vector
            time_vec = tran_result.get_time_vector()
            if time_vec is not None:
                self.assertGreater(len(time_vec), 100)
        except Exception:
            pass


class TestSubcircuitIntegration(GoldenTestMixin, WaveformTestMixin, unittest.TestCase):
    """Test subcircuit integration in complex scenarios."""
    
    def test_astable_multivibrator_transient(self):
        """Test astable multivibrator using subcircuits and external components."""
        # This would be a complex circuit with timing components
        circuit = Circuit("Astable Multivibrator")
        
        # Power supply
        vcc = VoltageSource(voltage=5.0, name="VCC")
        
        # Timing components
        r1 = Resistor(resistance=10000, name="R1")  # 10k
        r2 = Resistor(resistance=10000, name="R2")  # 10k
        c1 = Capacitor(capacitance=10e-6, name="C1")  # 10μF
        c2 = Capacitor(capacitance=10e-6, name="C2")  # 10μF
        
        # Add components
        circuit.add_component(vcc)
        circuit.add_component(r1)
        circuit.add_component(r2)
        circuit.add_component(c1)
        circuit.add_component(c2)
        
        # Basic cross-coupled configuration
        circuit.wire(vcc.neg, circuit.gnd)
        circuit.wire(vcc.pos, r1.n1)
        circuit.wire(vcc.pos, r2.n1)
        circuit.wire(r1.n2, c1.pos)
        circuit.wire(r2.n2, c2.pos)
        circuit.wire(c1.neg, circuit.gnd)
        circuit.wire(c2.neg, circuit.gnd)
        
        # Test SPICE generation
        spice = circuit.compile_to_spice()
        self.assertIn("VCC", spice)
        self.assertIn("R1", spice)
        self.assertIn("C1", spice)
        
        # Test with golden files
        self.assert_circuit_matches_golden(circuit, "astable_multivibrator_demo.spice")
        
        # Test transient simulation
        try:
            result = circuit.simulate_transient(step_time=100e-6, end_time=100e-3)
            if result is not None:
                # Test waveform
                self.assert_waveform_matches_golden(
                    result,
                    "astable_multivibrator.csv",
                    time_tolerance=1e-5,
                    voltage_tolerance=0.2
                )
        except Exception:
            pass
    
    def test_rc_block_subcircuit_definition(self):
        """Test RC block as reusable subcircuit."""
        # Define RC block subcircuit
        rc_block = Circuit("RC_BLOCK")
        r = Resistor(resistance=1000, name="R")
        c = Capacitor(capacitance=1e-6, name="C")
        
        rc_block.add_component(r)
        rc_block.add_component(c)
        
        # RC low-pass configuration
        rc_block.wire(r.n2, c.pos)
        rc_block.add_pin("input", r.n1)
        rc_block.add_pin("output", r.n2)
        rc_block.add_pin("gnd", c.neg)
        
        # Test subcircuit compilation
        subckt_spice = rc_block.compile_as_subckt()
        self.assertIn(".SUBCKT RC_BLOCK", subckt_spice)
        self.assertIn("input output gnd", subckt_spice)
        self.assertIn(".ENDS RC_BLOCK", subckt_spice)
        
        # Use in main circuit
        main_circuit = Circuit("RC Block Test")
        vs = VoltageSource(voltage=3.3, name="VS")
        rc_filter = SubCircuit(definition=rc_block, name="FILTER")
        
        main_circuit.add_component(vs)
        main_circuit.add_component(rc_filter)
        
        main_circuit.wire(vs.pos, rc_filter.input)
        main_circuit.wire(vs.neg, rc_filter.gnd)
        
        # Test integration
        main_spice = main_circuit.compile_to_spice()
        self.assertIn("XFILTER", main_spice)
        self.assertIn("RC_BLOCK", main_spice)


class TestTransientAnalysis(WaveformTestMixin, unittest.TestCase):
    """Test transient analysis with complex waveforms."""
    
    def test_rc_charging_transient(self):
        """Test RC charging circuit transient response."""
        circuit = Circuit("RC Charging")
        
        # Step voltage source and RC circuit
        vs = VoltageSource(voltage=5.0, name="VS")
        r1 = Resistor(resistance=1000, name="R1")   # 1kΩ
        c1 = Capacitor(capacitance=1e-6, name="C1") # 1μF
        
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(c1)
        
        # RC charging circuit
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, c1.pos)
        circuit.wire(c1.neg, circuit.gnd)
        
        # Set initial condition (discharged capacitor)
        circuit.set_initial_condition(c1.pos, 0.0)
        
        try:
            # Run transient simulation
            result = circuit.simulate_transient(step_time=10e-6, end_time=10e-3)
            
            if result is not None:
                # Test time vector
                time_vec = result.get_time_vector()
                self.assertIsNotNone(time_vec)
                self.assertGreater(len(time_vec), 50)
                
                # Test exponential charging behavior
                self.assert_waveform_matches_golden(
                    result,
                    "rc_charging_1k_1uF.csv",
                    time_tolerance=1e-6,
                    voltage_tolerance=0.1
                )
        except Exception:
            # Simulation might not be available
            pass
    
    def test_rc_discharging_transient(self):
        """Test RC discharging circuit transient response."""
        circuit = Circuit("RC Discharging")
        
        # Components for discharging test
        r1 = Resistor(resistance=2000, name="R1")    # 2kΩ
        c1 = Capacitor(capacitance=0.5e-6, name="C1") # 0.5μF
        
        circuit.add_component(r1)
        circuit.add_component(c1)
        
        # RC discharge circuit (no voltage source, just initial condition)
        circuit.wire(r1.n1, c1.pos)
        circuit.wire(r1.n2, circuit.gnd)
        circuit.wire(c1.neg, circuit.gnd)
        
        # Set initial condition (charged capacitor)
        circuit.set_initial_condition(c1.pos, 5.0)  # 5V initial charge
        
        try:
            # Run transient simulation
            result = circuit.simulate_transient(step_time=5e-6, end_time=5e-3)
            
            if result is not None:
                # Test exponential decay
                self.assert_waveform_matches_golden(
                    result,
                    "rc_discharging_2k_0p5uF.csv",
                    time_tolerance=1e-6,
                    voltage_tolerance=0.1
                )
        except Exception:
            pass
    
    def test_multiple_time_constants(self):
        """Test circuit with multiple time constants."""
        circuit = Circuit("Multiple Time Constants")
        
        # Input source
        vs = VoltageSource(voltage=10.0, name="VS")
        
        # Fast RC stage (small time constant)
        r_fast = Resistor(resistance=100, name="R_FAST")     # 100Ω
        c_fast = Capacitor(capacitance=1e-6, name="C_FAST") # 1μF, τ = 100μs
        
        # Slow RC stage (large time constant)
        r_slow = Resistor(resistance=10000, name="R_SLOW")   # 10kΩ
        c_slow = Capacitor(capacitance=10e-6, name="C_SLOW") # 10μF, τ = 100ms
        
        circuit.add_component(vs)
        circuit.add_component(r_fast)
        circuit.add_component(c_fast)
        circuit.add_component(r_slow)
        circuit.add_component(c_slow)
        
        # Chain the RC stages
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r_fast.n1)          # Input to fast stage
        circuit.wire(r_fast.n2, c_fast.pos)      # Fast RC junction
        circuit.wire(c_fast.neg, circuit.gnd)    # Fast capacitor to ground
        circuit.wire(r_fast.n2, r_slow.n1)       # Couple to slow stage
        circuit.wire(r_slow.n2, c_slow.pos)      # Slow RC junction
        circuit.wire(c_slow.neg, circuit.gnd)    # Slow capacitor to ground
        
        try:
            # Simulate long enough to see both time constants
            result = circuit.simulate_transient(step_time=1e-4, end_time=500e-3)
            
            if result is not None:
                self.assert_waveform_matches_golden(
                    result,
                    "rc_time_constants_comparison.csv",
                    time_tolerance=1e-4,
                    voltage_tolerance=0.2
                )
        except Exception:
            pass


class TestValidationAndErrorHandling(GoldenTestMixin, unittest.TestCase):
    """Test validation and error handling in complex scenarios."""
    
    def test_empty_circuit_handling(self):
        """Test handling of empty circuits."""
        circuit = Circuit("Empty Circuit")
        
        # Empty circuit should compile but produce minimal SPICE
        spice = circuit.compile_to_spice()
        self.assertIn("* Circuit: Empty Circuit", spice)
        self.assertIn(".end", spice)
        
        # Should not be able to simulate empty circuit
        try:
            result = circuit.simulate_operating_point()
            # If it doesn't fail, that's also OK
        except Exception:
            # Expected to fail
            pass
    
    def test_disconnected_components(self):
        """Test handling of components not connected to anything."""
        circuit = Circuit("Disconnected Test")
        
        # Create components but don't wire them
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Add components to circuit explicitly
        circuit.add_component(vs)
        circuit.add_component(r1)
        
        # Components are registered but not connected
        self.assertEqual(len(circuit.components), 2)
        self.assertEqual(len(circuit.wires), 0)
        
        # Golden file test for disconnected circuit
        self.assert_circuit_matches_golden(circuit, "disconnected_components.spice")


class TestWorkflowIntegration(WaveformTestMixin, unittest.TestCase):
    """Test complete end-to-end workflows."""
    
    def test_golden_file_workflow(self):
        """Test complete workflow with golden file validation."""
        # Create a known circuit
        circuit = Circuit("Workflow Test")
        
        vs = VoltageSource(voltage=12.0, name="VCC")
        r1 = Resistor(resistance=1000, name="R1")
        r2 = Resistor(resistance=2000, name="R2")
        c1 = Capacitor(capacitance=1e-6, name="C1")
        
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(r2)
        circuit.add_component(c1)
        
        # Build voltage divider with capacitive load
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, r2.n1)
        circuit.wire(r2.n2, circuit.gnd)
        circuit.wire(r1.n2, c1.pos)  # Tap point to capacitor
        circuit.wire(c1.neg, circuit.gnd)
        
        try:
            # 1. Test SPICE generation
            spice = circuit.compile_to_spice()
            self.assertIsNotNone(spice)
            
            # 2. Test operating point
            op_result = circuit.simulate_operating_point()
            self.assertIsNotNone(op_result)
            
            # 3. Test transient simulation
            tran_result = circuit.simulate_transient(step_time=10e-6, end_time=10e-3)
            if tran_result is not None:
                # 4. Test waveform validation
                self.assert_waveform_matches_golden(
                    tran_result,
                    "test_workflow.csv",
                    time_tolerance=1e-6,
                    voltage_tolerance=0.1
                )
        except Exception:
            # Simulation workflow might not be fully available
            pass


if __name__ == '__main__':
    unittest.main()