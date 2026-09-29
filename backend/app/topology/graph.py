import networkx as nx
from typing import List, Dict, Any, Optional, Set

class DependencyGraph:
    def __init__(self):
        # Directed graph where an edge (A, B) means "A depends on / calls B"
        self.graph = nx.DiGraph()
        self.raw_nodes = []
        self.raw_edges = []
        self.source = "configured"
        self.discovery_source = "Configured Topology"
        self.discovered_at = None

    def load_from_topology(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        source: str = "configured",
        discovery_source: str = "Configured Topology",
        discovered_at: Optional[str] = None
    ):
        self.graph.clear()
        self.raw_nodes = nodes
        self.raw_edges = edges
        self.source = source
        self.discovery_source = discovery_source
        self.discovered_at = discovered_at

        for node in nodes:
            node_id = node.get("id") or node.get("service_id")
            if node_id:
                self.graph.add_node(
                    node_id,
                    name=node.get("name", node_id),
                    type=node.get("type", "service"),
                    tier=node.get("tier", "core"),
                    criticality=node.get("criticality", "medium"),
                    status=node.get("status", node.get("live_status", "Operational"))
                )

        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src and tgt:
                self.graph.add_edge(
                    src,
                    tgt,
                    protocol=edge.get("protocol", "HTTP"),
                    type=edge.get("type", "sync"),
                    criticality=edge.get("criticality", "medium")
                )

    def get_nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                **data
            })
        return nodes

    def get_edges(self) -> List[Dict[str, Any]]:
        edges = []
        for src, tgt, data in self.graph.edges(data=True):
            edges.append({
                "source": src,
                "target": tgt,
                **data
            })
        return edges

    def get_upstream_services(self, service: str) -> List[str]:
        """
        Returns all services that `service` directly or indirectly depends on.
        If A -> B, B is upstream of A (A depends on B).
        """
        if service not in self.graph:
            return []
        # Successors in dependency graph (A -> B means A calls B)
        return list(nx.descendants(self.graph, service))

    def get_direct_upstream_services(self, service: str) -> List[str]:
        """Direct dependencies called by `service`."""
        if service not in self.graph:
            return []
        return list(self.graph.successors(service))

    def get_downstream_services(self, service: str) -> List[str]:
        """
        Returns all services that depend on `service` (callers that would be affected if `service` fails).
        If A -> B, A is downstream of B.
        """
        if service not in self.graph:
            return []
        # Predecessors in dependency graph
        return list(nx.ancestors(self.graph, service))

    def get_direct_downstream_services(self, service: str) -> List[str]:
        """Direct callers that depend on `service`."""
        if service not in self.graph:
            return []
        return list(self.graph.predecessors(service))

    def dependency_distance(self, source: str, target: str) -> Optional[int]:
        """
        Calculates shortest path distance between source and target.
        Checks both directed path (source -> target or target -> source) and undirected path.
        """
        if source not in self.graph or target not in self.graph:
            return None
        if source == target:
            return 0
        
        # Directed forward
        if nx.has_path(self.graph, source, target):
            return nx.shortest_path_length(self.graph, source, target)
        # Directed backward
        if nx.has_path(self.graph, target, source):
            return nx.shortest_path_length(self.graph, target, source)
        
        # Undirected fallback
        undirected = self.graph.to_undirected()
        if nx.has_path(undirected, source, target):
            return nx.shortest_path_length(undirected, source, target)

        return None

    def has_edge(self, source: str, target: str) -> bool:
        """Checks if a directed edge exists from source to target."""
        return self.graph.has_edge(source, target)

    def is_dependency_related(self, service_a: str, service_b: str) -> bool:
        """
        Checks if two services are connected in the dependency graph or share dependencies.
        """
        if service_a not in self.graph or service_b not in self.graph:
            return False
        if service_a == service_b:
            return True

        undirected = self.graph.to_undirected()
        return nx.has_path(undirected, service_a, service_b)

    def get_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Returns the shortest dependency path between source and target if one exists.
        """
        if source not in self.graph or target not in self.graph:
            return None
        if nx.has_path(self.graph, source, target):
            return nx.shortest_path(self.graph, source, target)
        if nx.has_path(self.graph, target, source):
            return nx.shortest_path(self.graph, target, source)
        
        undirected = self.graph.to_undirected()
        if nx.has_path(undirected, source, target):
            return nx.shortest_path(undirected, source, target)
        return None

    def get_dependencies(self, service: str) -> List[str]:
        """Convenience alias for direct dependencies called by service."""
        return self.get_direct_upstream_services(service)

    def get_dependents(self, service: str) -> List[str]:
        """Convenience alias for direct callers that depend on service."""
        return self.get_direct_downstream_services(service)

    def get_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Convenience alias for get_path."""
        return self.get_path(source, target)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": getattr(self, "source", "configured"),
            "discovered_at": getattr(self, "discovered_at", None),
            "discovery_source": getattr(self, "discovery_source", "Configured Topology"),
            "nodes": self.get_nodes(),
            "edges": self.get_edges(),
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

# Global singleton dependency graph instance
dependency_graph = DependencyGraph()
