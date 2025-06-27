# Example: Subcircuit functionality in zest
# This demonstrates how to define and use subcircuits

from zest import Circuit, Resistor, VoltageSource, SubCircuit

def create_divider_definition():
    """
    Defines a 2:1 voltage divider circuit.
    This function returns a Circuit object configured to be used as a subcircuit.
    """
    # 1. Create the circuit that will serve as the definition.
    #    The name "VOLTAGE_DIVIDER" will become the SPICE model name.
    divider_circuit = Circuit("VOLTAGE_DIVIDER")

    # 2. Add the internal components. These are encapsulated.
    r_top = Resistor(resistance=10000)  # 10k
    r_bottom = Resistor(resistance=10000)  # 10k

    # 3. Wire the internal components together.
    divider_circuit.wire(r_top.n2, r_bottom.n1)  # Connect the two resistors

    # 4. EXPOSE the external pins using the new `add_pin` method.
    #    This defines the public interface of the subcircuit.
    divider_circuit.add_pin("vin", r_top.n1)      # Pin 'vin' is the top of r_top
    divider_circuit.add_pin("vout", r_top.n2)     # Pin 'vout' is the middle node
    divider_circuit.add_pin("gnd", r_bottom.n2)   # Pin 'gnd' is the bottom of r_bottom

    return divider_circuit


def main():
    """Example usage of subcircuits."""
    # 1. Get the subcircuit definition from its factory function.
    divider_definition = create_divider_definition()

    # 2. Create the main (parent) circuit.
    main_circuit = Circuit("AudioAmplifierInputStage")

    # 3. Create other components for the main circuit.
    v_supply = VoltageSource(voltage=12.0)

    # 4. Instantiate the subcircuit definition as a new component.
    #    The `SubCircuit` object is treated just like a Resistor or Capacitor.
    bias_divider = SubCircuit(definition=divider_definition, name="U1_Bias")

    # 5. Wire the subcircuit instance into the main circuit.
    #    Access its pins as terminals (e.g., bias_divider.vin).
    main_circuit.wire(v_supply.pos, bias_divider.vin)
    main_circuit.wire(v_supply.neg, bias_divider.gnd)

    # The 'vout' pin of the subcircuit is now the bias voltage for the next stage.
    print("Bias divider vout pin:", bias_divider.vout)

    # 6. Compile and view the final SPICE netlist.
    spice_output = main_circuit.compile_to_spice()
    print("Generated SPICE netlist:")
    print("=" * 50)
    print(spice_output)
    print("=" * 50)

    # Example with multiple instances
    print("\n\nExample with multiple subcircuit instances:")
    print("=" * 50)
    
    # Create another circuit using multiple instances of the same subcircuit
    multi_circuit = Circuit("MultiDividerTest")
    v_source = VoltageSource(voltage=15.0)
    
    # Create two divider instances
    divider1 = SubCircuit(definition=divider_definition, name="U1")
    divider2 = SubCircuit(definition=divider_definition, name="U2")
    
    # Wire them in series
    multi_circuit.wire(v_source.pos, divider1.vin)
    multi_circuit.wire(divider1.vout, divider2.vin)
    multi_circuit.wire(v_source.neg, divider1.gnd)
    multi_circuit.wire(divider1.gnd, divider2.gnd)
    
    spice_multi = multi_circuit.compile_to_spice()
    print(spice_multi)


if __name__ == "__main__":
    main() 