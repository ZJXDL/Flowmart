from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parent


class SemanticRegistry:
    """
    Loads and exposes the Flowmart semantic contracts.

    The registry is intentionally lightweight:
    - metrics are loaded from semantic/metrics
    - dimensions are loaded from semantic/dimensions
    - relationships are loaded from semantic/relationships

    It acts as the bridge between the semantic contracts and downstream
    consumers such as the AI Analyst and BI integrations.
    """

    def __init__(self):
        self.metrics = {}
        self.dimensions = {}
        self.relationships = []

        self._load_metrics()
        self._load_dimensions()
        self._load_relationships()

    def _load_metrics(self):
        metrics_dir = ROOT / "metrics"

        for path in metrics_dir.glob("*.yml"):
            with path.open("r", encoding="utf-8") as file:
                document = yaml.safe_load(file) or {}

            for metric in document.get("metrics", []):
                name = metric["name"]
                self.metrics[name] = metric

    def _load_dimensions(self):
        dimensions_dir = ROOT / "dimensions"

        for path in dimensions_dir.glob("*.yml"):
            with path.open("r", encoding="utf-8") as file:
                document = yaml.safe_load(file) or {}

            for dimension in document.get("dimensions", []):
                name = dimension["name"]
                self.dimensions[name] = dimension

    def _load_relationships(self):
        relationships_dir = ROOT / "relationships"

        for path in relationships_dir.glob("*.yml"):
            with path.open("r", encoding="utf-8") as file:
                document = yaml.safe_load(file) or {}

            self.relationships.extend(
                document.get("relationships", [])
            )

    def get_metric(self, name):
        """Return a metric definition by name."""
        return self.metrics.get(name)

    def get_dimension(self, name):
        """Return a dimension definition by name."""
        return self.dimensions.get(name)

    def list_metrics(self):
        """Return all metric names."""
        return sorted(self.metrics.keys())

    def list_dimensions(self):
        """Return all dimension names."""
        return sorted(self.dimensions.keys())

    def list_relationships(self):
        """Return all relationship definitions."""
        return self.relationships

    def summary(self):
        """Return a high-level registry summary."""
        return {
            "metrics": len(self.metrics),
            "dimensions": len(self.dimensions),
            "relationships": len(self.relationships),
        }


if __name__ == "__main__":
    registry = SemanticRegistry()

    print("FLOWMART SEMANTIC REGISTRY")
    print("==========================")
    print(f"Metrics:       {len(registry.metrics)}")
    print(f"Dimensions:    {len(registry.dimensions)}")
    print(f"Relationships: {len(registry.relationships)}")

    print("\nMetrics:")
    for name in registry.list_metrics():
        metric = registry.get_metric(name)
        print(f"  - {name}: {metric.get('label', name)}")

    print("\nDimensions:")
    for name in registry.list_dimensions():
        dimension = registry.get_dimension(name)
        print(f"  - {name}: {dimension.get('label', name)}")