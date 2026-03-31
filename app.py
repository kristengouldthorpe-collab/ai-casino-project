from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

st.set_page_config(page_title="AI Casino Project V1", layout="wide")


@dataclass
class GameProfile:
    name: str
    category: str
    house_edge: float
    rounds_per_hour: int
    points_mode: str  # "coin_in" or "theo"
    dollars_per_point: float | None = None
    theo_per_point: float | None = None
    note: str = ""


GAME_PROFILES: Dict[str, GameProfile] = {
    "Reel Slots": GameProfile(
        name="Reel Slots",
        category="slots",
        house_edge=0.10,
        rounds_per_hour=500,
        points_mode="coin_in",
        dollars_per_point=5.0,
        note="Royal Caribbean publishes 1 point per $5 on reel slot machines.",
    ),
    "Video Poker": GameProfile(
        name="Video Poker",
        category="video_poker",
        house_edge=0.03,
        rounds_per_hour=500,
        points_mode="coin_in",
        dollars_per_point=10.0,
        note="Royal Caribbean publishes 1 point per $10 on video poker.",
    ),
    "Ultimate Texas Hold'em": GameProfile(
        name="Ultimate Texas Hold'em",
        category="table",
        house_edge=0.022,
        rounds_per_hour=40,
        points_mode="theo",
        theo_per_point=5.0,
        note="Royal does not publish a public table-game point formula, so this uses an editable estimate based on theoretical loss.",
    ),
    "Blackjack": GameProfile(
        name="Blackjack",
        category="table",
        house_edge=0.015,
        rounds_per_hour=70,
        points_mode="theo",
        theo_per_point=5.0,
        note="Royal does not publish a public table-game point formula, so this uses an editable estimate based on theoretical loss.",
    ),
    "Three Card Poker": GameProfile(
        name="Three Card Poker",
        category="table",
        house_edge=0.034,
        rounds_per_hour=50,
        points_mode="theo",
        theo_per_point=5.0,
        note="Royal does not publish a public table-game point formula, so this uses an editable estimate based on theoretical loss.",
    ),
    "Craps": GameProfile(
        name="Craps",
        category="table",
        house_edge=0.014,
        rounds_per_hour=45,
        points_mode="theo",
        theo_per_point=5.0,
        note="Royal does not publish a public table-game point formula, so this uses an editable estimate based on theoretical loss.",
    ),
}

# Seeded from a public Royal Caribbean campaign PDF; meant as an editable starter table.
OFFER_TIERS: List[Tuple[int, str, str]] = [
    (40000, "VIP2", "Top-tier instant reward / premium sailing access"),
    (25000, "D01", "High-tier balcony or stronger comp territory"),
    (15000, "D02", "Strong balcony / broad comp options"),
    (9000, "D02A", "Mid-high tier offer"),
    (6500, "D03", "Likely strong offer options"),
    (4000, "D03A", "Likely free-cruise territory on select sailings"),
    (3000, "D04", "Likely free interior / oceanview territory"),
    (2000, "D05", "Entry comp level"),
    (1500, "D06", "Lighter comp level / limited sailings"),
    (1200, "D07", "Starter instant reward level"),
    (800, "D08", "Smallest published starter tier in sample campaign"),
]


def calculate_metrics(
    profile: GameProfile,
    avg_bet: float,
    hours: float,
    rounds_per_hour_override: int | None = None,
    house_edge_override: float | None = None,
    dollars_per_point_override: float | None = None,
    theo_per_point_override: float | None = None,
) -> dict:
    rounds_per_hour = rounds_per_hour_override or profile.rounds_per_hour
    house_edge = (house_edge_override / 100.0) if house_edge_override is not None else profile.house_edge
    total_rounds = rounds_per_hour * hours
    total_coin_in = avg_bet * total_rounds
    theo = total_coin_in * house_edge

    if profile.points_mode == "coin_in":
        dollars_per_point = dollars_per_point_override or profile.dollars_per_point or 5.0
        points = total_coin_in / dollars_per_point
    else:
        theo_per_point = theo_per_point_override or profile.theo_per_point or 5.0
        points = theo / theo_per_point

    return {
        "rounds_per_hour": rounds_per_hour,
        "house_edge": house_edge,
        "total_rounds": total_rounds,
        "coin_in": total_coin_in,
        "theo": theo,
        "points": points,
    }



def likely_offer(points: float) -> tuple[str, str]:
    rounded = math.floor(points)
    for threshold, code, desc in OFFER_TIERS:
        if rounded >= threshold:
            return f"{code} tier (â‰¥ {threshold:,} pts)", desc
    return "Below starter comp tier", "Likely discount-only / weak offer territory based on the seeded sample campaign."



def build_fallback_explanation(game: str, metrics: dict, offer_label: str, offer_desc: str) -> str:
    points = metrics["points"]
    theo = metrics["theo"]
    coin_in = metrics["coin_in"]
    house_edge_pct = metrics["house_edge"] * 100

    if game in {"Reel Slots", "Video Poker"}:
        earn_comment = "This game earns points directly from coin-in, so your point pace is predictable."
    else:
        earn_comment = "This table-game estimate is driven by theoretical loss, so it is directionally useful but not official."

    return (
        f"You generated an estimated ${coin_in:,.0f} of action and ${theo:,.0f} of theoretical loss at an assumed {house_edge_pct:.1f}% house edge. "
        f"That translates to about {points:,.0f} points. {earn_comment} Based on the seeded offer ladder, that puts you in {offer_label}, which suggests {offer_desc.lower()} "
        f"If your goal is to maximize offers while controlling expected loss, compare this game against one or two alternatives before you play."
    )



def build_ai_prompt(game: str, avg_bet: float, hours: float, metrics: dict, offer_label: str, offer_desc: str) -> str:
    return f"""
You are a cruise casino comps coach.

Explain this simulation in plain English. Keep it practical, not academic.

Inputs:
- Game: {game}
- Average bet: ${avg_bet:,.2f}
- Hours played: {hours}
- Estimated rounds per hour: {metrics['rounds_per_hour']}
- Estimated coin-in: ${metrics['coin_in']:,.2f}
- Assumed house edge: {metrics['house_edge'] * 100:.2f}%
- Estimated theo: ${metrics['theo']:,.2f}
- Estimated points: {metrics['points']:,.0f}
- Likely offer tier: {offer_label}
- Offer interpretation: {offer_desc}

What to produce:
1. A 2-3 sentence summary of what this play level means.
2. A short strategy section: how good this game is for balancing offers vs losses.
3. One concrete recommendation.
4. One caution about uncertainty if the game is a table game.

Do not invent official Royal Caribbean formulas. If the game is a table game, explicitly say this is an estimate.
""".strip()


st.title("AI Casino Project â€” V1")
st.caption("Estimate casino points, theoretical loss, and likely cruise offer tiers.")

with st.expander("What this V1 does"):
    st.write(
        "This first version models casino play using public Royal Caribbean point rules for slots/video poker, "
        "plus editable estimates for table games. It then maps those points to a seeded offer ladder based on a public sample campaign."
    )

left, right = st.columns([1, 1])

with left:
    game = st.selectbox("Game", list(GAME_PROFILES.keys()))
    profile = GAME_PROFILES[game]

    avg_bet = st.number_input("Average bet per hand / spin ($)", min_value=0.0, value=25.0, step=5.0)
    hours = st.number_input("Hours played", min_value=0.0, value=4.0, step=0.5)

    st.subheader("Editable assumptions")
    rounds_per_hour_override = st.number_input(
        "Rounds / hands per hour",
        min_value=1,
        value=profile.rounds_per_hour,
        step=1,
    )
    house_edge_override = st.number_input(
        "House edge (%)",
        min_value=0.1,
        value=profile.house_edge * 100,
        step=0.1,
    )

    dollars_per_point_override = None
    theo_per_point_override = None

    if profile.points_mode == "coin_in":
        dollars_per_point_override = st.number_input(
            "Dollars wagered per point",
            min_value=0.1,
            value=float(profile.dollars_per_point or 5.0),
            step=0.5,
        )
    else:
        theo_per_point_override = st.number_input(
            "Estimated theo dollars per point",
            min_value=0.1,
            value=float(profile.theo_per_point or 5.0),
            step=0.5,
        )

    use_ai = st.checkbox("Generate AI explanation", value=False)

metrics = calculate_metrics(
    profile=profile,
    avg_bet=avg_bet,
    hours=hours,
    rounds_per_hour_override=rounds_per_hour_override,
    house_edge_override=house_edge_override,
    dollars_per_point_override=dollars_per_point_override,
    theo_per_point_override=theo_per_point_override,
)

offer_label, offer_desc = likely_offer(metrics["points"])

with right:
    st.subheader("Results")
    a, b, c = st.columns(3)
    a.metric("Estimated points", f"{metrics['points']:,.0f}")
    b.metric("Estimated theo", f"${metrics['theo']:,.0f}")
    c.metric("Likely tier", offer_label.split(" ")[0])

    st.write(f"**Likely offer tier:** {offer_label}")
    st.write(f"**Interpretation:** {offer_desc}")
    st.info(profile.note)

    st.subheader("How the math works")
    st.code(
        f"coin_in = avg_bet Ã— rounds_per_hour Ã— hours\n"
        f"coin_in = ${avg_bet:,.2f} Ã— {metrics['rounds_per_hour']} Ã— {hours} = ${metrics['coin_in']:,.2f}\n\n"
        f"theo = coin_in Ã— house_edge\n"
        f"theo = ${metrics['coin_in']:,.2f} Ã— {metrics['house_edge']*100:.2f}% = ${metrics['theo']:,.2f}\n\n"
        + (
            f"points = coin_in Ã· ${dollars_per_point_override:,.2f} per point\n"
            f"points = ${metrics['coin_in']:,.2f} Ã· ${dollars_per_point_override:,.2f} = {metrics['points']:,.0f}"
            if profile.points_mode == "coin_in"
            else f"points = theo Ã· ${theo_per_point_override:,.2f} theo per point\n"
            f"points = ${metrics['theo']:,.2f} Ã· ${theo_per_point_override:,.2f} = {metrics['points']:,.0f}"
        )
    )

st.subheader("Explanation")
if use_ai and OpenAI is not None and st.secrets.get("OPENAI_API_KEY"):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    prompt = build_ai_prompt(game, avg_bet, hours, metrics, offer_label, offer_desc)
    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )
        st.write(response.output_text)
    except Exception as e:
        st.warning(f"AI call failed, so fallback explanation is shown instead: {e}")
        st.write(build_fallback_explanation(game, metrics, offer_label, offer_desc))
else:
    st.write(build_fallback_explanation(game, metrics, offer_label, offer_desc))

with st.expander("Starter offer ladder used in V1"):
    st.write(
        "These thresholds are seeded from one public Royal Caribbean campaign PDF and should be treated as a starter ladder, not a universal truth."
    )
    st.table(
        [{"Points threshold": threshold, "Code": code, "Interpretation": desc} for threshold, code, desc in OFFER_TIERS]
    )

with st.expander("Good next upgrades"):
    st.markdown(
        """
- Add a compare mode: run two games side by side.
- Save scenarios to a history table.
- Replace the starter offer ladder with your own scraped or hand-curated examples.
- Let users enter cruise line rules separately for Royal, Carnival, MGM, etc.
- Add screenshots / OCR later if you want to parse real offers.
"""
    )
