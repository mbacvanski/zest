class Node:
    """
    Represents a node (connection point) in a circuit.
    """
    _node_counter = 0
    
    def __init__(self, name=None):
        if name is None:
            Node._node_counter += 1
            self.name = f"n{Node._node_counter}"
        else:
            self.name = name
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"Node('{self.name}')"


class GroundNode(Node):
    """
    Special node representing circuit ground.
    """
    def __init__(self):
        super().__init__("gnd")


# Create a global ground node instance
gnd = GroundNode() 