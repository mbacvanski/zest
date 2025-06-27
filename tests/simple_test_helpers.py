from zest import Circuit, SubCircuit, Component, Terminal, Resistor, Capacitor

def create_custom_resistor_definition() -> Circuit:
    """
    Creates a definition for a component that relies on an external .INCLUDE file.
    """
    resistor_definition = Circuit("CUSTOM_RESISTOR")

    # 1. Register the external file dependency.
    resistor_definition.add_include("tests/models/custom_resistor.lib")
    
    # 2. Mark this as external-only (defined in .INCLUDE file, not to be compiled)
    resistor_definition._is_external_only = True

    # 3. Define pins to match the .SUBCKT line in the model file.
    resistor_definition.add_pin("n1", Terminal(Component(), "p1"))
    resistor_definition.add_pin("n2", Terminal(Component(), "p2"))

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