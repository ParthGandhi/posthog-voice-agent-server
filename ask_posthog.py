import os
from dataclasses import dataclass
from typing import Any

import requests

POSTHOG_HOST = "https://us.posthog.com"
PROJECT_ID = "97299"


@dataclass
class PostHogResults:
    results: list[list[Any]] | None = None
    types: list[str] | None = None
    columns: list[str] | None = None


async def _convert_to_posthog_query(user_input: str) -> str:
    return ""


async def _execute_posthog_query(query: str) -> PostHogResults:
    # https://posthog.com/docs/sql#query-api
    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        raise ValueError("POSTHOG_API_KEY is not set")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
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


async def _generate_summary(query_results: PostHogResults) -> str:
    return ""


async def ask(user_input: str) -> str:
    query = await _convert_to_posthog_query(user_input)
    query = """select toDate(timestamp) as timestamp, count()
from events
group by timestamp
limit 100"""
    results = await _execute_posthog_query(query)
    summary = await _generate_summary(results)
    return summary
