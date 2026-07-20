"""
AI Insight Service — Phase 3 Upgrade
Generates structured insights with:
- Executive Summary
- Key Findings + KPIs
- Trend Analysis (fed from trend_detection.py)
- Risks
- Recommendations
"""

from app.core.ai_client import client
from app.services.trend_detection import (
    detect_trends,
    format_trends_for_prompt,
)


def generate_insights(question, data):
    """Generate rich, structured AI insights."""

    # Run programmatic trend detection first
    trends = detect_trends(data)
    trend_context = format_trends_for_prompt(trends)

    prompt = f"""
You are a senior data analyst providing business intelligence.

User Question:
{question}

Query Results (sample):
{data}

{f'''
Programmatic Analysis (pre-computed from the data):
{trend_context}
''' if trend_context else ''}

Generate a structured insight report using EXACTLY this format.
Use the section headers exactly as shown.

EXECUTIVE SUMMARY
Write 2-3 sentences summarizing the overall picture.
Include the most important number and what it means for the business.
If data shows change over time, state the percentage change and direction.

KEY FINDINGS
- List 3-5 specific findings with actual numbers from the data
- Calculate totals, averages, percentages where supported
- Highlight the highest and lowest values with context
- If the pre-computed analysis detected growth/decline trends, incorporate them
- If outliers were detected, explain their business significance

RISKS
- Identify 2-3 business risks visible in the data
- Include concentration risks if a few entities dominate
- Flag declining metrics, payment issues, or anomalies
- Each risk should reference specific data points

RECOMMENDATIONS
- Give 3-4 specific, actionable recommendations
- Each must directly address a finding or risk above
- Be concrete: "Increase X by Y%" not "Review data"
- Focus on: optimization, retention, revenue growth, cost reduction

Rules:
- Use plain text only, no markdown formatting
- Reference actual numbers from the results
- Never invent data not present in the results
- If only 1 row exists, focus on that data point's significance
- If no time periods exist, skip trend analysis
- Keep the total response under 250 words
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    raw_text = response.choices[0].message.content

    # Parse into structured sections
    sections = _parse_sections(raw_text)

    return sections


def _parse_sections(text):
    """Parse the AI response into structured JSON sections."""

    section_headers = [
        "EXECUTIVE SUMMARY",
        "KEY FINDINGS",
        "RISKS",
        "RECOMMENDATIONS",
    ]

    sections = {}
    current_section = None
    current_content = []

    for line in text.strip().split("\n"):
        stripped = line.strip()
        upper = stripped.upper()

        # Check if this line is a section header
        matched = False
        for header in section_headers:
            if header in upper:
                if current_section:
                    sections[current_section] = (
                        "\n".join(current_content).strip()
                    )
                current_section = header.lower().replace(
                    " ", "_"
                )
                current_content = []
                matched = True
                break

        if not matched and current_section:
            current_content.append(line)

    # Save the last section
    if current_section:
        sections[current_section] = (
            "\n".join(current_content).strip()
        )

    # If parsing failed, return as a single block
    if not sections:
        return {"executive_summary": text.strip()}

    return sections