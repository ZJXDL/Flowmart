from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from semantic.registry import SemanticRegistry


class SemanticBridge:
    """
    Provides the AI Analyst with structured access to the
    Flowmart semantic layer.

    The bridge keeps the AI Analyst decoupled from the YAML
    files themselves. The agent interacts with this interface,
    while SemanticRegistry handles loading the contracts.
    """

    def __init__(self):
        self.registry = SemanticRegistry()

    def get_available_metrics(self):
        """
        Return all available business metrics.
        """

        metrics = []

        for name in self.registry.list_metrics():
            metric = self.registry.get_metric(name)

            metrics.append(
                {
                    "name": name,
                    "label": metric.get("label"),
                    "description": metric.get("description"),
                    "model": metric.get("model"),
                    "expression": metric.get("expression"),
                    "type": metric.get("type"),
                    "unit": metric.get("unit"),
                    "time_dimension": metric.get(
                        "time_dimension"
                    ),
                }
            )

        return metrics

    def get_available_dimensions(self):
        """
        Return all available analytical dimensions.
        """

        dimensions = []

        for name in self.registry.list_dimensions():
            dimension = self.registry.get_dimension(name)

            dimensions.append(
                {
                    "name": name,
                    "label": dimension.get("label"),
                    "description": dimension.get(
                        "description"
                    ),
                    "type": dimension.get("type"),
                    "role": dimension.get("role"),
                    "column": dimension.get("column"),
                    "expression": dimension.get(
                        "expression"
                    ),
                }
            )

        return dimensions

    def get_relationships(self):
        """
        Return semantic relationship definitions.
        """

        return self.registry.list_relationships()

    def get_context(self):
        """
        Return a complete semantic context suitable for
        providing to an AI Analyst.
        """

        return {
            "metrics": self.get_available_metrics(),
            "dimensions": self.get_available_dimensions(),
            "relationships": self.get_relationships(),
        }


if __name__ == "__main__":
    bridge = SemanticBridge()

    context = bridge.get_context()

    print("FLOWMART AI ANALYST — SEMANTIC CONTEXT")
    print("======================================")

    print(
        f"Metrics:       {len(context['metrics'])}"
    )

    print(
        f"Dimensions:    {len(context['dimensions'])}"
    )

    print(
        f"Relationships: {len(context['relationships'])}"
    )

    print("\nAvailable Metrics:")

    for metric in context["metrics"]:
        print(
            f"  - {metric['name']}: "
            f"{metric['label']}"
        )

    print("\nAvailable Dimensions:")

    for dimension in context["dimensions"]:
        print(
            f"  - {dimension['name']}: "
            f"{dimension['label']}"
        )