import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import posthog
import requests
from posthog.ai.openai import OpenAI

posthog.project_api_key = os.getenv("POSTHOG_API_KEY")
posthog.host = "https://us.i.posthog.com"

client = OpenAI(posthog_client=posthog)

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


# TODO(pg): paginate possible insights, handle no metric being found
def _select_posthog_insight(
    insights: list[PostHogInsight], user_input: str
) -> PostHogInsight:
    insight_options = []
    for i, insight in enumerate(insights):
        if not insight.name and not insight.description:
            logger.warning(
                f"Skipping insight {insight.id} with empty name and description"
            )
            continue
        insight_options.append(
            {
                "id": i,
                "name": f"{insight.name} - {insight.description}",
            }
        )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to help me select the right metric. I will give you a user question and a list of available metrics. \nSelect the most appropriate metric based on what the user wants.\n\nFirst think through what the user is asking for and what the options are.  Show the output in <thinking>\n\nThen give me the final answer i",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "[{'id': 0, 'name': 'Pageview funnel, by browser - This example funnel shows how many of your users have completed 3 page views, broken down by browser.'}, {'id': 1, 'name': 'Referring domain (last 14 days) - Shows the most common referring domains for your users over the past 14 days.'}, {'id': 2, 'name': 'Growth accounting - How many of your users are new, returning, resurrecting, or dormant each week.'}, {'id': 3, 'name': 'Retention - Weekly retention of your users.'}, {'id': 4, 'name': 'Weekly active users (WAUs) - Shows the number of unique users that use your app every week.'}, {'id': 5, 'name': 'Daily active users (DAUs) - Shows the number of unique users that use your app every day.'}]",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": user_input}],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "metric_id",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "explanation": {
                            "type": "string",
                            "description": "A detailed explanation of the user's question and the metric that best answers it.",
                        },
                        "final_answer": {
                            "type": "number",
                            "description": "The unique identifier for the metric.",
                        },
                    },
                    "required": ["explanation", "final_answer"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.3,
        max_completion_tokens=2048,
    )

    response_json = json.loads(response.choices[0].message.content)  # type: ignore
    print(response_json)

    return insights[int(response_json["final_answer"])]


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
    analytics_results = insight.result
    analytics_metric_name = f"{insight.name} - {insight.description}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to give me a brief professional summary of a analytics result from Posthog. I will give you the query name and the results json, create a short summary that gives the gist of the metrics highlighting the important bits.",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(analytics_results),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Metric: {analytics_metric_name}"}
                ],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "analytics_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "explanation": {
                            "type": "string",
                            "description": "A detailed analysis of the user question and the analytics results",
                        },
                        "final_answer": {
                            "type": "string",
                            "description": "The summary of the analytics",
                        },
                    },
                    "required": ["explanation", "final_answer"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.3,
        max_completion_tokens=2048,
        top_p=1,
    )
    response_json = json.loads(response.choices[0].message.content)  # type: ignore
    print(response_json)
    return response_json["final_answer"]


async def ask(user_input: str) -> str:
    insights = await _get_posthog_insights()
    insight = _select_posthog_insight(insights, user_input)
    summary = await _generate_insight_summary(insight)
    return summary
