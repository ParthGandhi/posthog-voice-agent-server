import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

POSTHOG_HOST = "https://us.posthog.com"
PROJECT_ID = "97299"


@dataclass
class PostHogResults:
    results: list[list[Any]] | None = None
    types: list[str] | None = None
    columns: list[str] | None = None


@dataclass
class PostHogInsight:
    id: int
    short_id: str
    name: str
    derived_name: str | None
    filters: dict
    query: dict
    dashboards: list[int]
    result: Any | None
    description: str


def _get_posthog_headers() -> dict:
    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        raise ValueError("POSTHOG_API_KEY is not set")

    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


async def _get_posthog_insights() -> list[PostHogInsight]:
    headers = _get_posthog_headers()
    response = requests.get(
        f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/insights", headers=headers
    )

    response_json = response.json()
    print(response_json)
    return [
        PostHogInsight(
            id=insight["id"],
            short_id=insight["short_id"],
            name=insight["name"],
            derived_name=insight["derived_name"],
            filters=insight["filters"],
            query=insight["query"],
            dashboards=insight["dashboards"],
            result=insight["result"],
            description=insight["description"],
        )
        for insight in response_json["results"]
    ]


def _select_posthog_insight(
    insights: list[PostHogInsight], user_input: str
) -> PostHogInsight:
    insight_options = []
    for insight in insights:
        if not insight.name and not insight.description:
            logger.warning(
                f"Skipping insight {insight.id} with empty name and description"
            )
            continue
        insight_options.append(f"{insight.name} - {insight.description}")

    print(insight_options)
    raise ValueError("No insight found")


async def _execute_posthog_query(query: str) -> PostHogResults:
    headers = _get_posthog_headers()
    data = {
        "query": {
            "kind": "HogQLQuery",
            "query": query,
        }
    }
    response = requests.post(
        f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/query", headers=headers, json=data
    )

    response_json = response.json()
    print(response_json)
    return PostHogResults(
        results=response_json["results"],
        types=response_json["types"],
        columns=response_json["columns"],
    )


async def _generate_insight_summary(insight: PostHogInsight) -> str:
    return ""


async def ask(user_input: str) -> str:
    insights = await _get_posthog_insights()
    insight = _select_posthog_insight(insights, user_input)
    summary = await _generate_insight_summary(insight)
    return summary
