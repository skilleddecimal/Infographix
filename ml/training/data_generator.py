"""Synthetic training data generator for ML models."""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ml.config import get_ml_settings


@dataclass
class TrainingExample:
    """A single training example."""

    prompt: str
    archetype: str
    parameters: dict[str, Any]
    dsl: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


@dataclass
class PromptTemplate:
    """Template for generating prompts."""

    patterns: list[str]
    archetype: str
    param_generators: dict[str, callable] = field(default_factory=dict)


class SyntheticDataGenerator:
    """Generates synthetic training data for ML models.

    Creates varied prompts with corresponding archetypes and parameters
    by combining template patterns with random variations.
    """

    # Topic words for different domains
    TOPICS = {
        "sales": ["leads", "prospects", "customers", "deals", "revenue", "pipeline", "conversion"],
        "marketing": ["awareness", "engagement", "acquisition", "retention", "brand", "campaign"],
        "product": ["ideation", "design", "development", "testing", "launch", "iteration"],
        "project": ["planning", "execution", "monitoring", "completion", "review", "delivery"],
        "business": ["strategy", "operations", "growth", "optimization", "transformation"],
        "hr": ["recruitment", "onboarding", "training", "performance", "retention", "culture"],
        "tech": ["research", "prototype", "development", "testing", "deployment", "maintenance"],
    }

    # Number words
    NUMBERS = {
        "three": 3, "3": 3, "four": 4, "4": 4, "five": 5, "5": 5,
        "six": 6, "6": 6, "seven": 7, "7": 7, "eight": 8, "8": 8,
    }

    # Time periods
    TIME_PERIODS = ["Q1", "Q2", "Q3", "Q4", "2024", "2025", "January", "February", "March",
                    "Phase 1", "Phase 2", "Phase 3", "Week 1", "Month 1", "Year 1"]

    def __init__(self):
        self.settings = get_ml_settings()
        self.templates = self._build_templates()

    def _build_templates(self) -> dict[str, list[PromptTemplate]]:
        """Build prompt templates for each archetype."""
        return {
            "funnel": [
                PromptTemplate(
                    patterns=[
                        "Create a {count} stage sales funnel showing {stages}",
                        "Make a funnel diagram with {count} levels for {topic}",
                        "I need a {topic} funnel with {count} stages",
                        "Show me a conversion funnel from {stage1} to {stage2}",
                        "Design a {count}-step funnel for our {topic} process",
                        "Build a marketing funnel showing customer journey",
                        "Create a lead generation funnel with {count} stages",
                    ],
                    archetype="funnel",
                    param_generators={
                        "count": lambda: random.choice([3, 4, 5, 6]),
                        "topic": lambda: random.choice(["sales", "marketing", "conversion", "lead generation"]),
                    },
                ),
            ],
            "pyramid": [
                PromptTemplate(
                    patterns=[
                        "Create a {count} tier pyramid showing {topic}",
                        "Make a hierarchy pyramid with {count} levels",
                        "I need a pyramid diagram for {topic}",
                        "Show organizational hierarchy as a pyramid",
                        "Design a {count}-level priority pyramid",
                        "Build a Maslow-style needs pyramid",
                        "Create a pyramid showing {stage1} at top and {stage2} at bottom",
                    ],
                    archetype="pyramid",
                    param_generators={
                        "count": lambda: random.choice([3, 4, 5]),
                        "topic": lambda: random.choice(["priorities", "hierarchy", "needs", "goals"]),
                    },
                ),
            ],
            "timeline": [
                PromptTemplate(
                    patterns=[
                        "Create a timeline showing {count} milestones",
                        "Make a project timeline from {date1} to {date2}",
                        "I need a roadmap with {count} phases",
                        "Show our product roadmap for {year}",
                        "Design a {count}-month timeline for {topic}",
                        "Build a project schedule with key milestones",
                        "Create a history timeline showing {count} events",
                    ],
                    archetype="timeline",
                    param_generators={
                        "count": lambda: random.choice([4, 5, 6, 7, 8]),
                        "year": lambda: random.choice(["2024", "2025", "2026"]),
                        "topic": lambda: random.choice(["product launch", "project", "company history"]),
                    },
                ),
            ],
            "process": [
                PromptTemplate(
                    patterns=[
                        "Create a {count} step process flow for {topic}",
                        "Make a workflow diagram showing {count} stages",
                        "I need a process diagram for {topic}",
                        "Show the steps from {stage1} to {stage2}",
                        "Design a {count}-step procedure for {topic}",
                        "Build a step-by-step guide with {count} steps",
                        "Create a linear process with {count} phases",
                    ],
                    archetype="process",
                    param_generators={
                        "count": lambda: random.choice([4, 5, 6, 7]),
                        "topic": lambda: random.choice(["onboarding", "approval", "development", "review"]),
                    },
                ),
            ],
            "cycle": [
                PromptTemplate(
                    patterns=[
                        "Create a {count} phase cycle diagram",
                        "Make a continuous improvement cycle",
                        "I need a circular process with {count} stages",
                        "Show the PDCA cycle",
                        "Design a feedback loop with {count} steps",
                        "Build a recurring process diagram",
                        "Create a wheel diagram with {count} segments",
                    ],
                    archetype="cycle",
                    param_generators={
                        "count": lambda: random.choice([4, 5, 6]),
                    },
                ),
            ],
            "hub_spoke": [
                PromptTemplate(
                    patterns=[
                        "Create a hub and spoke diagram with {count} spokes",
                        "Make a central concept with {count} related ideas",
                        "I need a radial diagram showing {topic}",
                        "Show a central {center} with {count} connected elements",
                        "Design a mind map style diagram",
                        "Build a diagram with core concept and {count} branches",
                        "Create a radial layout with {count} outer elements",
                    ],
                    archetype="hub_spoke",
                    param_generators={
                        "count": lambda: random.choice([4, 5, 6, 8]),
                        "center": lambda: random.choice(["strategy", "customer", "product", "team"]),
                        "topic": lambda: random.choice(["stakeholders", "features", "departments"]),
                    },
                ),
            ],
            "matrix": [
                PromptTemplate(
                    patterns=[
                        "Create a {rows}x{cols} matrix for {topic}",
                        "Make a 2x2 matrix showing {quadrants}",
                        "I need a grid comparing {axis1} vs {axis2}",
                        "Show a SWOT analysis matrix",
                        "Design a priority matrix with {rows} rows and {cols} columns",
                        "Build a comparison grid for {topic}",
                        "Create a quadrant diagram for {topic}",
                    ],
                    archetype="matrix",
                    param_generators={
                        "rows": lambda: random.choice([2, 3, 4]),
                        "cols": lambda: random.choice([2, 3, 4]),
                        "topic": lambda: random.choice(["priorities", "features", "risks", "options"]),
                    },
                ),
            ],
            "comparison": [
                PromptTemplate(
                    patterns=[
                        "Create a comparison between {option1} and {option2}",
                        "Make a versus diagram showing pros and cons",
                        "I need to compare {count} options",
                        "Show side by side comparison of {topic}",
                        "Design a before and after comparison",
                        "Build a feature comparison table",
                        "Create a pros vs cons layout",
                    ],
                    archetype="comparison",
                    param_generators={
                        "count": lambda: random.choice([2, 3, 4]),
                        "topic": lambda: random.choice(["products", "solutions", "approaches", "vendors"]),
                    },
                ),
            ],
            "org_chart": [
                PromptTemplate(
                    patterns=[
                        "Create an org chart for our {department} team",
                        "Make an organizational structure diagram",
                        "I need a hierarchy showing reporting lines",
                        "Show our company structure",
                        "Design a team organization chart",
                        "Build a management hierarchy diagram",
                        "Create a department structure visualization",
                    ],
                    archetype="org_chart",
                    param_generators={
                        "department": lambda: random.choice(["engineering", "marketing", "sales", "product"]),
                    },
                ),
            ],
            "venn": [
                PromptTemplate(
                    patterns=[
                        "Create a {count} circle Venn diagram",
                        "Make a Venn diagram showing overlap between {topics}",
                        "I need a diagram showing intersection of {count} concepts",
                        "Show the relationship between {topic1} and {topic2}",
                        "Design a Venn diagram for {count} categories",
                        "Build an overlapping circles diagram",
                    ],
                    archetype="venn",
                    param_generators={
                        "count": lambda: random.choice([2, 3]),
                    },
                ),
            ],
            "gauge": [
                PromptTemplate(
                    patterns=[
                        "Create a gauge showing {metric} at {value}%",
                        "Make a meter diagram for {metric}",
                        "I need a progress gauge showing {value}%",
                        "Show a KPI meter for {metric}",
                        "Design a speedometer style chart",
                        "Build a performance gauge",
                    ],
                    archetype="gauge",
                    param_generators={
                        "metric": lambda: random.choice(["performance", "progress", "satisfaction", "efficiency"]),
                        "value": lambda: random.randint(20, 95),
                    },
                ),
            ],
            "bullet_list": [
                PromptTemplate(
                    patterns=[
                        "Create a bullet list with {count} items about {topic}",
                        "Make an icon list showing {count} features",
                        "I need a checklist with {count} items",
                        "Show {count} key points about {topic}",
                        "Design a feature list with icons",
                        "Build a benefits list with {count} items",
                    ],
                    archetype="bullet_list",
                    param_generators={
                        "count": lambda: random.choice([4, 5, 6, 7, 8]),
                        "topic": lambda: random.choice(["features", "benefits", "steps", "requirements"]),
                    },
                ),
            ],
            "flowchart": [
                PromptTemplate(
                    patterns=[
                        "Create a flowchart for {process}",
                        "Make a decision tree with {count} branches",
                        "I need a flowchart showing {topic} process",
                        "Show a decision flowchart for {topic}",
                        "Design a process flowchart with decisions",
                        "Build an algorithm flowchart",
                    ],
                    archetype="flowchart",
                    param_generators={
                        "count": lambda: random.choice([2, 3, 4]),
                        "process": lambda: random.choice(["approval", "review", "decision", "support"]),
                        "topic": lambda: random.choice(["customer support", "bug triage", "hiring"]),
                    },
                ),
            ],
        }

    def generate_prompt(self, archetype: str) -> TrainingExample:
        """Generate a single training example for an archetype.

        Args:
            archetype: The target archetype.

        Returns:
            TrainingExample with prompt and metadata.
        """
        if archetype not in self.templates:
            raise ValueError(f"Unknown archetype: {archetype}")

        template = random.choice(self.templates[archetype])
        pattern = random.choice(template.patterns)

        # Generate parameter values
        params = {}
        for key, generator in template.param_generators.items():
            params[key] = generator()

        # Add common parameters
        if "stages" not in params and "{stages}" in pattern:
            domain = random.choice(list(self.TOPICS.keys()))
            stages = random.sample(self.TOPICS[domain], min(4, len(self.TOPICS[domain])))
            params["stages"] = ", ".join(stages)

        if "stage1" not in params and "{stage1}" in pattern:
            domain = random.choice(list(self.TOPICS.keys()))
            stages = random.sample(self.TOPICS[domain], 2)
            params["stage1"] = stages[0]
            params["stage2"] = stages[1]

        if "date1" not in params and "{date1}" in pattern:
            dates = random.sample(self.TIME_PERIODS, 2)
            params["date1"] = dates[0]
            params["date2"] = dates[1]

        if "quadrants" not in params and "{quadrants}" in pattern:
            params["quadrants"] = "high/low priority and high/low effort"

        if "axis1" not in params and "{axis1}" in pattern:
            params["axis1"] = random.choice(["effort", "impact", "risk", "cost"])
            params["axis2"] = random.choice(["value", "urgency", "feasibility", "benefit"])

        if "option1" not in params and "{option1}" in pattern:
            params["option1"] = "Option A"
            params["option2"] = "Option B"

        if "topics" not in params and "{topics}" in pattern:
            params["topics"] = "design, development, and testing"

        if "topic1" not in params and "{topic1}" in pattern:
            params["topic1"] = random.choice(["skills", "knowledge", "experience"])
            params["topic2"] = random.choice(["passion", "opportunity", "market need"])

        # Format the prompt
        try:
            prompt = pattern.format(**params)
        except KeyError as e:
            # Fallback if a placeholder is missing
            prompt = pattern.split("{")[0] + f" for {archetype}"

        return TrainingExample(
            prompt=prompt,
            archetype=archetype,
            parameters=params,
        )

    def generate_dataset(
        self,
        samples_per_archetype: int = 100,
        archetypes: list[str] | None = None,
    ) -> list[TrainingExample]:
        """Generate a complete training dataset.

        Args:
            samples_per_archetype: Number of examples per archetype.
            archetypes: List of archetypes to include (default: all).

        Returns:
            List of TrainingExample objects.
        """
        if archetypes is None:
            archetypes = list(self.templates.keys())

        examples = []
        for archetype in archetypes:
            for _ in range(samples_per_archetype):
                example = self.generate_prompt(archetype)
                examples.append(example)

        # Shuffle the dataset
        random.shuffle(examples)
        return examples

    def save_dataset(
        self,
        examples: list[TrainingExample],
        output_path: Path | str,
        format: str = "jsonl",
    ) -> None:
        """Save dataset to file.

        Args:
            examples: List of training examples.
            output_path: Output file path.
            format: Output format ('jsonl' or 'json').
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "prompt": ex.prompt,
                "archetype": ex.archetype,
                "parameters": ex.parameters,
            }
            for ex in examples
        ]

        if format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item) + "\n")
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def load_dataset(self, input_path: Path | str) -> list[TrainingExample]:
        """Load dataset from file.

        Args:
            input_path: Input file path (jsonl or json).

        Returns:
            List of TrainingExample objects.
        """
        input_path = Path(input_path)
        examples = []

        if input_path.suffix == ".jsonl":
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    examples.append(TrainingExample(
                        prompt=data["prompt"],
                        archetype=data["archetype"],
                        parameters=data.get("parameters", {}),
                    ))
        else:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    examples.append(TrainingExample(
                        prompt=item["prompt"],
                        archetype=item["archetype"],
                        parameters=item.get("parameters", {}),
                    ))

        return examples
