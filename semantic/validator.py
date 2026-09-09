from pathlib import Path
import argparse
import subprocess

import yaml


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent


class SemanticValidator:
    """
    Validates the Flowmart semantic contracts.

    Default mode performs static contract validation and does not require
    Docker or Trino. Integration mode additionally validates the semantic
    contract against the live Trino orders schema.
    """

    def __init__(self, integration=False):
        self.integration = integration

        self.errors = []
        self.warnings = []

        self.metrics = {}
        self.dimensions = {}
        self.relationships = []
        self.model = None

        self._load_contracts()

    def _load_yaml(self, path):
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def _load_contracts(self):
        metrics_path = ROOT / "metrics" / "ecommerce.yml"
        dimensions_path = ROOT / "dimensions" / "orders.yml"
        relationships_path = ROOT / "relationships" / "model.yml"

        metrics_document = self._load_yaml(metrics_path)
        dimensions_document = self._load_yaml(dimensions_path)
        relationships_document = self._load_yaml(
            relationships_path
        )

        self.metrics = {
            metric["name"]: metric
            for metric in metrics_document.get("metrics", [])
        }

        self.dimensions = {
            dimension["name"]: dimension
            for dimension in dimensions_document.get("dimensions", [])
        }

        self.relationships = relationships_document.get(
            "relationships",
            [],
        )

        models = relationships_document.get("models", [])

        if models:
            self.model = models[0]

    def _get_trino_columns(self):
        """
        Retrieve the actual orders schema from the local Trino container.

        This method is only called in integration mode.
        """

        command = [
            "docker",
            "exec",
            "atlas-trino",
            "trino",
            "--server",
            "http://localhost:8080",
            "--user",
            "flowmart",
            "--catalog",
            "iceberg",
            "--schema",
            "atlas",
            "--execute",
            "DESCRIBE orders",
        ]

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            self.errors.append(
                "Unable to query the Trino orders schema."
            )

            if result.stderr.strip():
                self.errors.append(
                    result.stderr.strip()
                )

            return set()

        columns = set()

        for line in result.stdout.splitlines():
            line = line.strip()

            if not line:
                continue

            parts = [
                part.strip().strip('"')
                for part in line.split(",")
            ]

            if parts:
                columns.add(parts[0])

        return columns

    def validate_contract_names(self):
        if len(self.metrics) != 9:
            self.errors.append(
                f"Expected 9 metrics, found {len(self.metrics)}."
            )

        if len(self.dimensions) != 6:
            self.errors.append(
                f"Expected 6 dimensions, found {len(self.dimensions)}."
            )

        if len(self.relationships) != 3:
            self.errors.append(
                "Expected 3 relationships, found "
                f"{len(self.relationships)}."
            )

        if self.model is None:
            self.errors.append(
                "No semantic model definition was found."
            )

    def validate_model(self):
        if self.model is None:
            return

        if self.model.get("name") != "orders":
            self.errors.append(
                "Semantic model must be named 'orders'."
            )

        if self.model.get("grain") != "one row per order":
            self.errors.append(
                "Orders grain must be 'one row per order'."
            )

        primary_key = self.model.get("primary_key", [])

        if primary_key != ["order_id"]:
            self.errors.append(
                "orders primary key must be order_id."
            )

    def validate_metrics(self):
        for name, metric in self.metrics.items():
            if metric.get("model") != "orders":
                self.errors.append(
                    f"Metric '{name}' does not target "
                    "the orders model."
                )

            if not metric.get("expression"):
                self.errors.append(
                    f"Metric '{name}' has no expression."
                )

            if not metric.get("label"):
                self.warnings.append(
                    f"Metric '{name}' has no display label."
                )

            if not metric.get("description"):
                self.warnings.append(
                    f"Metric '{name}' has no description."
                )

    def validate_dimensions(self, trino_columns=None):
        for name, dimension in self.dimensions.items():
            column = dimension.get("column")

            if column:
                if (
                    self.integration
                    and trino_columns is not None
                    and column not in trino_columns
                ):
                    self.errors.append(
                        f"Dimension '{name}' references missing "
                        f"Trino column '{column}'."
                    )

            elif not dimension.get("expression"):
                self.errors.append(
                    f"Dimension '{name}' has neither a column "
                    "nor an expression."
                )

    def validate_relationships(self, trino_columns=None):
        for relationship in self.relationships:
            name = relationship.get(
                "name",
                "<unnamed>",
            )

            source = relationship.get("from", {})
            source_model = source.get("model")
            source_column = source.get("column")

            if source_model != "orders":
                self.errors.append(
                    f"Relationship '{name}' does not originate "
                    "from the orders model."
                )

            if (
                self.integration
                and trino_columns is not None
                and source_column not in trino_columns
            ):
                self.errors.append(
                    f"Relationship '{name}' references missing "
                    f"source column '{source_column}'."
                )

            status = relationship.get("status")

            if status not in {"logical", "planned"}:
                self.errors.append(
                    f"Relationship '{name}' has invalid status "
                    f"'{status}'."
                )

    def validate_model_lists(self):
        if self.model is None:
            return

        model_metrics = set(
            self.model.get("metrics", [])
        )

        actual_metrics = set(
            self.metrics.keys()
        )

        missing_metrics = actual_metrics - model_metrics
        unknown_metrics = model_metrics - actual_metrics

        if missing_metrics:
            self.errors.append(
                "Metrics missing from the orders model: "
                + ", ".join(sorted(missing_metrics))
            )

        if unknown_metrics:
            self.errors.append(
                "Unknown metrics listed in the orders model: "
                + ", ".join(sorted(unknown_metrics))
            )

        model_dimensions = set(
            self.model.get("dimensions", [])
        )

        actual_dimensions = set(
            self.dimensions.keys()
        )

        missing_dimensions = (
            actual_dimensions - model_dimensions
        )

        unknown_dimensions = (
            model_dimensions - actual_dimensions
        )

        if missing_dimensions:
            self.errors.append(
                "Dimensions missing from the orders model: "
                + ", ".join(sorted(missing_dimensions))
            )

        if unknown_dimensions:
            self.errors.append(
                "Unknown dimensions listed in the orders model: "
                + ", ".join(sorted(unknown_dimensions))
            )

    def validate(self):
        self.validate_contract_names()
        self.validate_model()
        self.validate_metrics()

        trino_columns = None

        if self.integration:
            trino_columns = self._get_trino_columns()

            if not trino_columns:
                return False

        self.validate_dimensions(trino_columns)
        self.validate_relationships(trino_columns)
        self.validate_model_lists()

        return not self.errors

    def print_report(self, success):
        print("FLOWMART SEMANTIC VALIDATOR")
        print("==========================")
        print(f"Metrics:       {len(self.metrics)}")
        print(f"Dimensions:    {len(self.dimensions)}")
        print(f"Relationships: {len(self.relationships)}")

        if self.integration:
            print("Mode:          integration")
        else:
            print("Mode:          static")

        if self.errors:
            print("\nERRORS:")

            for error in self.errors:
                print(f"  [ERROR] {error}")

        if self.warnings:
            print("\nWARNINGS:")

            for warning in self.warnings:
                print(f"  [WARN]  {warning}")

        print()

        if success:
            print("SEMANTIC VALIDATION PASSED")
        else:
            print("SEMANTIC VALIDATION FAILED")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate the Flowmart semantic layer."
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help=(
            "Also validate the semantic contract against "
            "the local atlas-trino container."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    validator = SemanticValidator(
        integration=args.integration
    )

    success = validator.validate()

    validator.print_report(success)

    raise SystemExit(0 if success else 1)