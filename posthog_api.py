import logging
import os
from dataclasses import dataclass
from typing import Any, List

import requests

logger = logging.getLogger(__name__)

POSTHOG_HOST = "https://us.posthog.com"
PROJECT_ID = "9270"


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


@dataclass
class PostHogDashboard:
    id: int
    name: str
    description: str | None


async def get_all_dashboards() -> List[PostHogDashboard]:
    base_url = f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/dashboards"
    results = await _get_all_paginated_results(base_url)

    return [
        PostHogDashboard(
            id=dashboard["id"],
            name=dashboard["name"],
            description=dashboard["description"],
        )
        for dashboard in results
    ]


async def get_all_insights() -> List[PostHogInsight]:
    base_url = f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/insights"
    results = await _get_all_paginated_results(base_url)

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
        for insight in results
    ]


def _get_posthog_headers() -> dict:
    api_key = os.getenv("POSTHOG_PERSONAL_API_KEY")
    if not api_key:
        raise ValueError("POSTHOG_PERSONAL_API_KEY is not set")

    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


async def _get_all_paginated_results(base_url: str) -> list[dict]:
    """Helper function to get all paginated results from a PostHog API endpoint"""
    headers = _get_posthog_headers()
    all_results = []
    next_url = base_url

    while next_url:
        response = requests.get(next_url, headers=headers)
        response_json = response.json()

        all_results.extend(response_json["results"])
        next_url = response_json.get("next")

    return all_results


async def get_insight_embed_url(insight_id: int) -> str | None:
    headers = _get_posthog_headers()
    url = f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/insights/{insight_id}/sharing/"

    response = requests.get(url, headers=headers)
    data = response.json()

    if data.get("enabled") and data.get("access_token"):
        return _get_sharing_url(data["access_token"])
    return None


async def get_dashboard_embed_url(dashboard_id: int) -> str | None:
    headers = _get_posthog_headers()
    url = f"{POSTHOG_HOST}/api/projects/{PROJECT_ID}/dashboards/{dashboard_id}/sharing/"

    response = requests.get(url, headers=headers)
    data = response.json()

    if data.get("enabled") and data.get("access_token"):
        return _get_sharing_url(data["access_token"])
    return None


def _get_sharing_url(token: str) -> str:
    return f"{POSTHOG_HOST}/embedded/{token}"
