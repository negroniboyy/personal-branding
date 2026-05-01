#!/usr/bin/env python3
"""Update learning state from reviewed content-sheet rows.

The rows file must be JSON and contain a list of objects with at least:
ID, Title, Review decision, Content, Category, Channel, Planner Source

A legacy Proposal ID column is also accepted as fallback input.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ReviewDelta:
    approved: int = 0
    disapproved: int = 0
    edited_title: int = 0
    edited_brief: int = 0


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value) -> str:
    return str(value or "").strip()


def derive_patterns(state: dict) -> list[str]:
    proposals: dict[str, dict] = state.get("proposals", {})
    approved_categories = Counter()
    disapproved_categories = Counter()
    title_edit_categories = Counter()

    for proposal in proposals.values():
        category = normalize(proposal.get("category")) or "Unknown"
        decision = normalize(proposal.get("review_decision"))
        if decision == "Approved":
            approved_categories[category] += 1
        elif decision == "Disapproved":
            disapproved_categories[category] += 1
        if proposal.get("edited_title"):
            title_edit_categories[category] += 1

    patterns: list[str] = []
    for category, count in approved_categories.most_common():
        if count >= 2:
            patterns.append(f"Repeated approvals in `{category}` suggest this category is currently aligned.")
    for category, count in disapproved_categories.most_common():
        if count >= 2:
            patterns.append(f"Repeated disapprovals in `{category}` suggest this angle needs reframing before reuse.")
    for category, count in title_edit_categories.most_common():
        if count >= 2:
            patterns.append(f"Titles in `{category}` are often edited, so propose plainer wording first.")
    return patterns


def update_state(rows: list[dict], state: dict) -> tuple[dict, ReviewDelta]:
    proposals = state.setdefault("proposals", {})
    summary = state.setdefault(
        "summary",
        {
            "approved_count": 0,
            "disapproved_count": 0,
            "edited_title_count": 0,
            "edited_brief_count": 0,
        },
    )
    delta = ReviewDelta()

    for row in rows:
        content_id = normalize(row.get("ID") or row.get("Proposal ID"))
        if not content_id:
            continue
        title = normalize(row.get("Title"))
        content = normalize(row.get("Content"))
        decision = normalize(row.get("Review decision"))
        category = normalize(row.get("Category"))
        channel = normalize(row.get("Channel"))
        planner_source = normalize(row.get("Planner Source"))

        entry = proposals.get(
            content_id,
            {
                "initial_title": title,
                "initial_content": content,
                "category": category,
                "channel": channel,
                "planner_source": planner_source,
                "review_decision": "",
                "current_title": title,
                "current_content": content,
                "edited_title": False,
                "edited_brief": False,
            },
        )

        edited_title = title and title != normalize(entry.get("initial_title"))
        edited_brief = content and content != normalize(entry.get("initial_content"))

        if edited_title and not entry.get("edited_title"):
            delta.edited_title += 1
            summary["edited_title_count"] += 1
        if edited_brief and not entry.get("edited_brief"):
            delta.edited_brief += 1
            summary["edited_brief_count"] += 1

        previous_decision = normalize(entry.get("review_decision"))
        if decision == "Approved" and previous_decision != "Approved":
            delta.approved += 1
            summary["approved_count"] += 1
        elif decision == "Disapproved" and previous_decision != "Disapproved":
            delta.disapproved += 1
            summary["disapproved_count"] += 1

        entry.update(
            {
                "category": category or entry.get("category", ""),
                "channel": channel or entry.get("channel", ""),
                "planner_source": planner_source or entry.get("planner_source", ""),
                "review_decision": decision,
                "current_title": title or entry.get("current_title", ""),
                "current_content": content or entry.get("current_content", ""),
                "edited_title": entry.get("edited_title", False) or edited_title,
                "edited_brief": entry.get("edited_brief", False) or edited_brief,
            }
        )
        proposals[content_id] = entry

    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["learned_patterns"] = derive_patterns(state)
    return state, delta


def render_markdown(state: dict) -> str:
    lines = [
        "# Learned Patterns",
        "",
        "Use this file as the compact human-readable summary of what the user tends to approve.",
        "",
        "Update it only after review outcomes are available for rows with `ID`.",
        "Prefer repeated behavior over one-off edits.",
        "",
        "## Current Signals",
        "",
    ]
    patterns = state.get("learned_patterns") or ["No confirmed learned patterns yet."]
    for pattern in patterns:
        lines.append(f"- {pattern}")
    lines.extend(
        [
            "",
            "## Update Format",
            "",
            "Write short operational bullets such as:",
            "",
            "- Prefer titles that sound like a real thought after real work, not a hook.",
            "- Avoid binary or overly rhetorical openings.",
            "- Prefer titles that name workflow tension over titles that sound clever.",
            "",
            "Do not add speculative rules. Every added rule should be traceable to reviewed rows.",
            "",
        ]
    )
    return "
".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-file", required=True, help="JSON file containing reviewed sheet rows")
    parser.add_argument("--state-file", required=True, help="Path to learning-state.json")
    parser.add_argument("--patterns-file", required=True, help="Path to learned-patterns.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_json(Path(args.rows_file))
    state = load_json(Path(args.state_file))
    state, delta = update_state(rows, state)

    Path(args.state_file).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "
", encoding="utf-8")
    Path(args.patterns_file).write_text(render_markdown(state), encoding="utf-8")
    print(
        "approved_added={approved} disapproved_added={disapproved} edited_titles_added={edited_title} edited_briefs_added={edited_brief}".format(
            approved=delta.approved,
            disapproved=delta.disapproved,
            edited_title=delta.edited_title,
            edited_brief=delta.edited_brief,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
