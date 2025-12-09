"""
Normalization script: Post-processes transcripts.json to add normalized fields
using Claude API to map free-text values to standard categories.

Usage:
    python normalize.py                 # Normalize all fields
    python normalize.py --dry-run       # Show unique values without normalizing
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = Path("data/transcripts.json")

# Standard categories for normalization
INDUSTRY_CATEGORIES = [
    "Technology",
    "Healthcare",
    "Finance/Banking",
    "Education",
    "Marketing/Advertising",
    "Legal",
    "Media/Entertainment",
    "Manufacturing",
    "Retail/E-commerce",
    "Government",
    "Non-profit",
    "Creative/Arts",
    "Consulting",
    "Real Estate",
    "Other",
]

JOB_CATEGORIES = [
    "Software Engineering",
    "Data/Analytics",
    "Product Management",
    "Design/UX",
    "Marketing",
    "Sales",
    "Customer Support",
    "Operations",
    "Finance/Accounting",
    "Human Resources",
    "Legal",
    "Healthcare Professional",
    "Educator/Academic",
    "Writer/Content Creator",
    "Artist/Creative",
    "Consultant",
    "Executive/Leadership",
    "Administrative",
    "Research/Science",
    "Other",
]

USE_CASE_CATEGORIES = [
    "Writing/Editing",
    "Code Assistance",
    "Research/Information Gathering",
    "Data Analysis",
    "Brainstorming/Ideation",
    "Email/Communication",
    "Summarization",
    "Learning/Education",
    "Content Creation",
    "Administrative Tasks",
    "Customer Interaction",
    "Translation",
    "Problem Solving",
    "Other",
]

PAIN_POINT_CATEGORIES = [
    "Accuracy/Hallucinations",
    "Context Limitations",
    "Lack of Domain Knowledge",
    "Output Quality",
    "Speed/Performance",
    "Cost",
    "Privacy/Security Concerns",
    "Integration Difficulties",
    "Inconsistent Results",
    "Learning Curve",
    "Trust Issues",
    "Limited Creativity",
    "Other",
]


def load_transcripts() -> dict:
    """Load transcripts from JSON file."""
    with open(DATA_FILE) as f:
        return json.load(f)


def save_transcripts(data: dict):
    """Save transcripts to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_unique_values(transcripts: list, field: str, is_list: bool = False) -> list[str]:
    """Extract unique non-empty values for a field."""
    values = set()
    for t in transcripts:
        val = t.get(field)
        if not val or val == "UNKNOWN":
            continue
        if is_list and isinstance(val, list):
            for item in val:
                if item and item != "UNKNOWN":
                    values.add(item)
        elif isinstance(val, str):
            values.add(val)
    return sorted(values)


def normalize_with_claude(
    client: anthropic.Anthropic,
    values: list[str],
    categories: list[str],
    field_name: str,
) -> dict:
    """Use Claude to map values to standard categories."""
    if not values:
        return {}

    categories_str = "\n".join(f"- {c}" for c in categories)
    values_str = json.dumps(values, indent=2)

    prompt = f"""Map each of these {field_name} values from interview transcripts to one of the standard categories below.

Standard categories:
{categories_str}

Values to map:
{values_str}

Return ONLY a valid JSON object mapping each input value to exactly one category.
Example format: {{"input value 1": "Category A", "input value 2": "Category B"}}

Important:
- Every input value must appear as a key in your response
- Each value must map to exactly one of the standard categories listed above
- Use "Other" only if no category fits well
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()

    # Try to parse JSON from response
    try:
        # Find JSON object in response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response_text[start:end])
    except json.JSONDecodeError:
        pass

    raise ValueError(f"Could not parse mapping from response: {response_text[:500]}")


def apply_normalization(
    transcripts: list,
    field: str,
    mapping: dict,
    new_field: str,
    is_list: bool = False,
):
    """Apply normalization mapping to transcripts."""
    for t in transcripts:
        val = t.get(field)
        if not val or val == "UNKNOWN":
            t[new_field] = "UNKNOWN"
            continue

        if is_list and isinstance(val, list):
            normalized = []
            for item in val:
                if item and item in mapping:
                    normalized.append(mapping[item])
                elif item:
                    normalized.append("Other")
            # Remove duplicates while preserving order
            seen = set()
            t[new_field] = [x for x in normalized if not (x in seen or seen.add(x))]
        elif isinstance(val, str):
            t[new_field] = mapping.get(val, "Other")


def main():
    parser = argparse.ArgumentParser(description="Normalize transcript fields")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show unique values without normalizing"
    )
    args = parser.parse_args()

    print(f"Loading transcripts from {DATA_FILE}...")
    data = load_transcripts()
    transcripts = data["transcripts"]
    print(f"Loaded {len(transcripts)} transcripts")

    # Get unique values for each field
    fields_to_normalize = [
        ("industry", "industry_normalized", INDUSTRY_CATEGORIES, False),
        ("job_title", "job_category", JOB_CATEGORIES, False),
        ("primary_use_cases", "use_case_categories", USE_CASE_CATEGORIES, True),
        ("key_pain_points", "pain_point_categories", PAIN_POINT_CATEGORIES, True),
    ]

    for field, new_field, categories, is_list in fields_to_normalize:
        unique_values = get_unique_values(transcripts, field, is_list)
        print(f"\n{field}: {len(unique_values)} unique values")

        if args.dry_run:
            # Show top 20 most common values
            counter = Counter()
            for t in transcripts:
                val = t.get(field)
                if is_list and isinstance(val, list):
                    counter.update(val)
                elif val and val != "UNKNOWN":
                    counter[val] += 1
            print("Top 20 values:")
            for val, count in counter.most_common(20):
                print(f"  {count:4d}: {val}")
            continue

    if args.dry_run:
        print("\nDry run complete. Run without --dry-run to normalize.")
        return

    # Normalize each field
    client = anthropic.Anthropic()

    for field, new_field, categories, is_list in fields_to_normalize:
        unique_values = get_unique_values(transcripts, field, is_list)
        if not unique_values:
            print(f"\n{field}: No values to normalize")
            continue

        print(f"\nNormalizing {field} ({len(unique_values)} unique values)...")

        # Process in batches if there are many values
        batch_size = 100
        full_mapping = {}

        for i in range(0, len(unique_values), batch_size):
            batch = unique_values[i : i + batch_size]
            print(f"  Processing batch {i // batch_size + 1} ({len(batch)} values)...")

            mapping = normalize_with_claude(client, batch, categories, field)
            full_mapping.update(mapping)

        # Apply normalization
        apply_normalization(transcripts, field, full_mapping, new_field, is_list)
        print(f"  Added {new_field} field")

    # Save updated transcripts
    print(f"\nSaving to {DATA_FILE}...")
    save_transcripts(data)
    print("Done!")


if __name__ == "__main__":
    main()
