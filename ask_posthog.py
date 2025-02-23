import asyncio
import json
import logging
import os
from dataclasses import dataclass

import posthog
from posthog.ai.openai import AsyncOpenAI, OpenAI

import posthog_api
from posthog_api import PostHogDashboard, PostHogInsight

posthog.project_api_key = os.getenv("POSTHOG_PROJECT_API_KEY")
posthog.host = "https://us.i.posthog.com"

openai_client = OpenAI(posthog_client=posthog)
openai_async_client = AsyncOpenAI(posthog_client=posthog)

logger = logging.getLogger(__name__)


@dataclass
class PosthogQueryResult:
    summary: str
    embed_url: str | None


def _select_posthog_insight(
    insights: list[PostHogInsight], user_input: str
) -> PostHogInsight | None:
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

    response = openai_client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to help me select the right metric. I will give you a user question and a list of available metrics. \nSelect the most appropriate metric based on what the user wants.\n\nFirst think through what the user is asking for and what the options are. \n\nThen give me the final answer as the index of the insight that best matches. If no matching index is found, use -1",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(insight_options),
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
    if response_json["final_answer"] == -1:
        return None
    return insights[int(response_json["final_answer"])]


async def _generate_insight_summary(insight: PostHogInsight) -> str:
    analytics_results = insight.result
    analytics_metric_name = f"{insight.name} - {insight.description}"
    response = await openai_async_client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to give me a brief professional summary of a analytics result from Posthog. I will give you the query name and the results json, create a short summary that gives the gist of the metrics highlighting the important information and data. Only present the data, do not give suggestions.",
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


async def ask(user_input: str) -> PosthogQueryResult:
    insights = await posthog_api.get_all_insights()
    insight = _select_posthog_insight(insights, user_input)
    if not insight:
        return PosthogQueryResult(
            summary="I couldn't find a relevant metric that matches your query. Please try rephrasing your question or ask about a different metric.",
            embed_url=None,
        )
    summary = await _generate_insight_summary(insight)
    embed_url = await posthog_api.get_insight_embed_url(insight.id)
    return PosthogQueryResult(summary=summary, embed_url=embed_url)


def _select_dashboard(
    dashboards: list[PostHogDashboard], user_input: str
) -> PostHogDashboard | None:
    dashboard_options = [
        {
            "id": i,
            "name": dashboard.name,
            "description": dashboard.description or "No description",
        }
        for i, dashboard in enumerate(dashboards)
    ]

    response = openai_client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to help select the most relevant dashboard based on a user query. Consider the dashboard names and descriptions to find the best match. \n First think through what the user is asking for and what the options are. \n Then give me the final answer as the index of the dashboard that best matches. If no matching index is found, use -1",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(dashboard_options),
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
                "name": "dashboard_id",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "explanation": {
                            "type": "string",
                            "description": "A detailed explanation of why this dashboard was selected",
                        },
                        "final_answer": {
                            "type": "number",
                            "description": "The index of the selected dashboard",
                        },
                    },
                    "required": ["explanation", "final_answer"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.3,
    )

    response_json = json.loads(response.choices[0].message.content)
    if response_json["final_answer"] == -1:
        return None
    return dashboards[int(response_json["final_answer"])]


async def _get_dashboard_insights(dashboard_id: int) -> list[PostHogInsight]:
    insights = await posthog_api.get_all_insights()
    return [insight for insight in insights if dashboard_id in insight.dashboards]


def _combine_summaries(
    dashboard: PostHogDashboard,
    insights: list[PostHogInsight],
    insight_summaries: list[str],
) -> str:
    summary_parts = [
        f"Dashboard: {dashboard.name} - {dashboard.description or ''}",
        "Insights:",
    ]

    # Add numbered insights
    for i, (insight, summary) in enumerate(zip(insights, insight_summaries), 1):
        summary_parts.append(f"{i}. {insight.name} - {insight.description} - {summary}")

    combined_summary_str = "\n".join(summary_parts)

    response = openai_client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Your task is to give me a brief professional summary of an analytics dashboard from Posthog. I will give you a dashboard name, and a list of insights from that dashboard. Create a short summary that highlights the important insights about the entire dashboard. Only present the condensed insights, not suggestions. Include key metrics and numbers.",
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": combined_summary_str,
                    }
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
                            "description": "A detailed analysis of the dashboard and the insights",
                        },
                        "final_answer": {
                            "type": "string",
                            "description": "The summary of the dashboard",
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


async def _generate_dashboard_summary(
    dashboard: PostHogDashboard, insights: list[PostHogInsight]
) -> str:
    if not insights:
        return f"Dashboard '{dashboard.name}' has no insights to summarize."

    # Generate summaries for all insights in parallel
    insight_summaries = await asyncio.gather(
        *[_generate_insight_summary(insight) for insight in insights]
    )

    return _combine_summaries(dashboard, insights, insight_summaries)


async def summarize_dashboard(user_input: str) -> PosthogQueryResult:
    dashboards = await posthog_api.get_all_dashboards()
    dashboard = _select_dashboard(dashboards, user_input)
    if not dashboard:
        return PosthogQueryResult(
            summary="I couldn't find a relevant dashboard that matches your query. Please try rephrasing your question or ask about a different dashboard.",
            embed_url=None,
        )
    insights = await _get_dashboard_insights(dashboard.id)
    summary = await _generate_dashboard_summary(dashboard, insights)
    embed_url = await posthog_api.get_dashboard_embed_url(dashboard.id)
    return PosthogQueryResult(summary=summary, embed_url=embed_url)
