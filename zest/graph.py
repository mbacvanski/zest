class Graph:
    """
    Simple undirected graph to represent circuit connectivity.
    """
    def __init__(self):
        self.nodes = set()
        self.edges = []

    def add_node(self, node):
        self.nodes.add(node)

    def add_edge(self, node1, node2):
        self.edges.append((node1, node2))

    def remove_node(self, node):
        self.nodes.discard(node)
        self.edges = [e for e in self.edges if node not in e]

    def remove_edge(self, node1, node2):
        self.edges = [e for e in self.edges if e != (node1, node2) and e != (node2, node1)] 