from zest import Circuit, SubCircuit, Component, Terminal, Resistor, Capacitor

def create_custom_resistor_definition() -> Circuit:
    """
    Creates a definition for a component that relies on an external .INCLUDE file.
    """
    import os
    
    resistor_definition = Circuit("CUSTOM_RESISTOR")

    # 1. Register the external file dependency with absolute path
    model_path = os.path.join(os.path.dirname(__file__), "models", "custom_resistor.lib")
    resistor_definition.add_include(model_path)
    
    # 2. Mark this as external-only (defined in .INCLUDE file, not to be compiled)
    resistor_definition._is_external_only = True

    # 3. Define pins to match the .SUBCKT line in the model file.
    # Create dummy components and add them to the circuit for pin definitions
    dummy_comp1 = Component()
    dummy_comp2 = Component()
    resistor_definition.add_component(dummy_comp1)
    resistor_definition.add_component(dummy_comp2)
    
    resistor_definition.add_pin("n1", Terminal(dummy_comp1, "p1"))
    resistor_definition.add_pin("n2", Terminal(dummy_comp2, "p2"))

    return resistor_definition

class CustomResistor(SubCircuit):
    """
    A user-friendly wrapper for the CUSTOM_RESISTOR subcircuit.
    """
    _definition = None # Class-level cache

    def __init__(self, name=None):
        if not CustomResistor._definition:
            CustomResistor._definition = create_custom_resistor_definition()

        super().__init__(definition=CustomResistor._definition, name=name)

def create_rc_stage_definition() -> Circuit:
    """
    Defines a single RC filter stage using a regular resistor.
    This entire block will be instantiated as a subcircuit.
    """
    rc_stage_circuit = Circuit("RC_FILTER_STAGE")

    # Internal components - use regular resistor for simplicity
    r1 = Resistor(resistance=10e3, name="R_internal")  # 10kΩ
    c1 = Capacitor(capacitance=1e-6, name="C_internal") # 1uF
    
    # Set initial condition so that the voltage across the capacitor is 0V
    rc_stage_circuit.set_initial_condition(c1.pos, 0.0)
    
    # Explicitly add components to the circuit
    rc_stage_circuit.add_component(r1)
    rc_stage_circuit.add_component(c1)

    # Internal wiring
    rc_stage_circuit.wire(r1.n2, c1.pos)

    # Expose pins
    rc_stage_circuit.add_pin("vin", r1.n1)
    rc_stage_circuit.add_pin("vout", r1.n2)
    rc_stage_circuit.add_pin("gnd", c1.neg)

    return rc_stage_circuit

def create_rc_stage_with_custom_resistor_definition() -> Circuit:
    """
    Defines a single RC filter stage using a custom resistor from an include file.
    This tests the include file handling and subcircuit instantiation.
    """
    rc_stage_circuit = Circuit("RC_FILTER_STAGE_CUSTOM")

    # Internal components - use custom resistor from include file
    r1 = CustomResistor(name="R_custom")  # 10kΩ custom resistor
    c1 = Capacitor(capacitance=1e-6, name="C_internal") # 1uF
    
    # Set initial condition so that the voltage across the capacitor is 0V
    rc_stage_circuit.set_initial_condition(c1.pos, 0.0)
    
    # Explicitly add components to the circuit
    rc_stage_circuit.add_component(r1)
    rc_stage_circuit.add_component(c1)

    # Internal wiring - connect custom resistor output to capacitor
    rc_stage_circuit.wire(r1.n2, c1.pos)

    # Expose pins
    rc_stage_circuit.add_pin("vin", r1.n1)
    rc_stage_circuit.add_pin("vout", r1.n2)
    rc_stage_circuit.add_pin("gnd", c1.neg)

    return rc_stage_circuit

def create_voltage_divider_with_custom_resistors_definition() -> Circuit:
    """
    Defines a voltage divider using two custom resistors from an include file.
    This is a different subcircuit type from RC filter that also uses custom_resistor.lib.
    """
    divider_circuit = Circuit("VOLTAGE_DIVIDER_CUSTOM")

    # Two custom resistors for voltage division
    r1 = CustomResistor(name="R1_custom")  # Top resistor
    r2 = CustomResistor(name="R2_custom")  # Bottom resistor
    
    # Explicitly add components to the circuit
    divider_circuit.add_component(r1)
    divider_circuit.add_component(r2)

    # Internal wiring - series connection
    divider_circuit.wire(r1.n2, r2.n1)

    # Expose pins
    divider_circuit.add_pin("vin", r1.n1)      # Input voltage
    divider_circuit.add_pin("vout", r1.n2)     # Output voltage (middle node)
    divider_circuit.add_pin("gnd", r2.n2)      # Ground

    return divider_circuit 