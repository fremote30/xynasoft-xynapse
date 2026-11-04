import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def generate_dashboard_insights(data: dict) -> list:
    """
    Generate AI-powered insights.
    Falls back safely if OpenAI is not configured.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    # =========================
    # 🚨 SAFE FALLBACK (NO KEY)
    # =========================
    if not api_key or OpenAI is None:
        return fallback_insights(data)

    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""
You are an expert church growth and sermon analytics assistant.

Analyze the following data and give 3-5 actionable insights for a pastor.

DATA:
- Total Sermons: {data.get("total_sermons")}
- Total Shares: {data.get("total_shares")}
- Top Sermons: {data.get("top_sermons")}

INSTRUCTIONS:
- Be concise
- Be practical
- Use simple language
- Focus on growth and engagement
- Output as bullet points
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You help pastors grow their impact."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        text = response.choices[0].message.content or ""

        insights = [
            line.strip("•- ")
            for line in text.split("\n")
            if line.strip()
        ]

        return insights if insights else fallback_insights(data)

    except Exception as e:
        print("OpenAI error:", e)
        return fallback_insights(data)


# =========================
# 🔥 FALLBACK ENGINE (CRITICAL)
# =========================
def fallback_insights(data: dict) -> list:

    total_sermons = data.get("total_sermons", 0)
    total_shares = data.get("total_shares", 0)

    insights = []

    if total_sermons == 0:
        return [
            "✍️ Start by creating your first sermon.",
            "📣 Share sermons to begin reaching members."
        ]

    avg_shares = total_shares / total_sermons if total_sermons else 0

    if avg_shares > 5:
        insights.append("🔥 Strong engagement. Your sermons are widely shared.")
    elif avg_shares > 2:
        insights.append("📈 Engagement is growing. Stay consistent.")
    else:
        insights.append("⚡ Try sharing sermons more to increase reach.")

    if total_sermons < 5:
        insights.append("✍️ Create more sermons to build momentum.")
    else:
        insights.append("🚀 You're building consistency. Keep going.")

    # Optional: Top sermon hint
    top = data.get("top_sermons", [])
    if top:
        insights.append(f"🏆 '{top[0]['title']}' is your top-performing sermon.")

    return insights