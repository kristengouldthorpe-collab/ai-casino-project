from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

import streamlit as st

st.set_page_config(page_title="Royal Caribbean Casino Royale", layout="centered")

# -----------------------------
# Styling
# -----------------------------
ROYAL_BLUE = "#123B8F"
ROYAL_GOLD = "#F7C948"
ROYAL_LIGHT = "#F4F7FC"
TEXT_DARK = "#1C2A3A"

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(180deg, #ffffff 0%, {ROYAL_LIGHT} 100%);
    }}
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 860px;
    }}
    h1, h2, h3 {{
        color: {ROYAL_BLUE};
    }}
    .playful-divider {{
        font-size: 1.1rem;
        letter-spacing: 0.25rem;
        color: {ROYAL_GOLD};
        margin: 0.4rem 0 1rem 0;
        text-align: center;
        font-weight: 700;
    }}
    .hero-card {{
        background: white;
        border: 1px solid rgba(18,59,143,0.12);
        border-left: 8px solid {ROYAL_BLUE};
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(18,59,143,0.08);
        margin-bottom: 1rem;
    }}
    .result-card {{
        background: white;
        border: 1px solid rgba(18,59,143,0.12);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 8px 24px rgba(18,59,143,0.08);
        margin: 0.4rem 0 0.8rem 0;
    }}
    .result-label {{
        color: {ROYAL_BLUE};
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
        text-transform: none;
    }}
    .result-value {{
        color: {TEXT_DARK};
        font-size: 1.9rem;
        font-weight: 800;
        line-height: 1.2;
    }}
    .small-note {{
        font-size: 0.92rem;
        color: #4B5D79;
    }}
    .benefit-box {{
        background: #ffffff;
        border: 1px solid rgba(247,201,72,0.45);
        border-radius: 14px;
        padding: 0.85rem 1rem;
        margin-top: 0.8rem;
    }}
    ul {{
        margin-bottom: 0.2rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Data model
# -----------------------------
@dataclass
class GameProfile:
    name: str
    house_edge: float
    rounds_per_hour: int
    points_mode: str  # coin_in or theoretical_loss
    dollars_per_point: float | None = None
    theoretical_loss_per_point: float | None = None
    note: str = ""


GAME_PROFILES: Dict[str, GameProfile] = {
    "Reel Slots": GameProfile(
        name="Reel Slots",
        house_edge=0.10,
        rounds_per_hour=500,
        points_mode="coin_in",
        dollars_per_point=5.0,
        note="Royal Caribbean publishes 1 point for every $5 of coin-in on reel slots.",
    ),
    "Video Poker": GameProfile(
        name="Video Poker",
        house_edge=0.03,
        rounds_per_hour=500,
        points_mode="coin_in",
        dollars_per_point=10.0,
        note="Royal Caribbean publishes 1 point for every $10 of coin-in on video poker.",
    ),
    "Ultimate Texas Hold'em": GameProfile(
        name="Ultimate Texas Hold'em",
        house_edge=0.022,
        rounds_per_hour=40,
        points_mode="theoretical_loss",
        theoretical_loss_per_point=5.0,
        note="Royal Caribbean does not publish a simple public point formula for table games, so this uses an estimate based on theoretical loss.",
    ),
    "Blackjack": GameProfile(
        name="Blackjack",
        house_edge=0.015,
        rounds_per_hour=70,
        points_mode="theoretical_loss",
        theoretical_loss_per_point=5.0,
        note="Royal Caribbean does not publish a simple public point formula for table games, so this uses an estimate based on theoretical loss.",
    ),
    "Three Card Poker": GameProfile(
        name="Three Card Poker",
        house_edge=0.034,
        rounds_per_hour=50,
        points_mode="theoretical_loss",
        theoretical_loss_per_point=5.0,
        note="Royal Caribbean does not publish a simple public point formula for table games, so this uses an estimate based on theoretical loss.",
    ),
    "Craps": GameProfile(
        name="Craps",
        house_edge=0.0075,
        rounds_per_hour=10,
        points_mode="coin_in",
        dollars_per_point=15.0,
        note="Royal Caribbean does not publish a simple public point formula for table games, so this model assumes disciplined play and estimates points based on reports from other players.",
    ),
}


GOAL_OPTIONS: List[tuple[str, int]] = [
    ("Prime 2,500 points", 2500),
    ("Signature 25,000 points", 25000),
    ("Masters 100,000 points", 100000),
    ("400 points", 400),
    ("600 points", 600),
    ("800 points", 800),
    ("1,200 points", 1200),
    ("1,500 points", 1500),
    ("2,000 points", 2000),
    ("3,000 points", 3000),
    ("4,000 points", 4000),
    ("6,500 points", 6500),
    ("9,000 points", 9000),
    ("15,000 points", 15000),
    ("40,000 points", 40000),
]


TIER_BENEFITS = {
    "Prime": [
        "Waived convenience fee for cashless wagering on your SeaPass card",
        "Complimentary drinks in Casino Royale during operating hours",
        "Discount on VOOM Surf & Stream internet packages",
        "Exclusive rates for family and friends on additional staterooms",
        "Annual complimentary interior stateroom on one cruise",
        "Tier priority contact number",
    ],
    "Signature": [
        "Everything included with Prime",
        "Complimentary Wi-Fi for 1 device",
        "$350 jewelry and boutique credit",
        "15% Vitality Spa discount",
        "Annual complimentary balcony stateroom on one cruise",
        "Special offers with partnership casinos",
    ],
    "Masters": [
        "Everything included with Signature",
        "Complimentary Wi-Fi for 2 devices",
        "$550 jewelry and boutique credit",
        "20% Vitality Spa discount",
        "Priority entertainment access and dining reservations",
        "Onboard credit",
        "Priority access at the terminal",
        "Carry-on bag drop off with priority delivery to your stateroom",
        "Welcome lunch in the Main Dining Room",
        "Coastal Kitchen access on eligible ships",
        "Flexible departure with a la carte breakfast",
        "Annual complimentary Grand Suite on one cruise",
    ],
}


def calculate_goal_results(
    profile: GameProfile,
    average_bet: float,
    goal_points: int,
    rounds_per_hour: int,
    house_edge_percent: float,
) -> dict:
    house_edge = house_edge_percent / 100.0

    if profile.points_mode == "coin_in":
        dollars_per_point = float(profile.dollars_per_point or 5.0)
        required_coin_in = goal_points * dollars_per_point
        required_theoretical_loss = required_coin_in * house_edge
        required_rounds = required_coin_in / average_bet if average_bet > 0 else 0
        required_hours = required_rounds / rounds_per_hour if rounds_per_hour > 0 else 0
    else:
        theoretical_loss_per_point = float(profile.theoretical_loss_per_point or 5.0)
        required_theoretical_loss = goal_points * theoretical_loss_per_point
        required_coin_in = required_theoretical_loss / house_edge if house_edge > 0 else 0
        required_rounds = required_coin_in / average_bet if average_bet > 0 else 0
        required_hours = required_rounds / rounds_per_hour if rounds_per_hour > 0 else 0

    return {
        "required_hours": required_hours,
        "required_theoretical_loss": required_theoretical_loss,
        "required_coin_in": required_coin_in,
        "required_rounds": required_rounds,
        "house_edge": house_edge,
    }



def get_tier_name(goal_points: int) -> str | None:
    if goal_points >= 100000:
        return "Masters"
    if goal_points >= 25000:
        return "Signature"
    if goal_points >= 2500:
        return "Prime"
    return None



def human_explanation(game: str, goal_points: int, results: dict, profile: GameProfile) -> str:
    hours = results["required_hours"]
    loss = results["required_theoretical_loss"]
    coin_in = results["required_coin_in"]
    rounds = results["required_rounds"]
    tier_name = get_tier_name(goal_points)

    if hours < 1:
        timing_text = f"less than an hour of play"
    elif hours < 10:
        timing_text = f"about {hours:,.1f} hours of play"
    else:
        timing_text = f"about {hours:,.0f} hours of play"

    base = (
        f"To reach {goal_points:,} points playing {game}, you would need about {timing_text}. "
        f"That works out to around {rounds:,.0f} hands or spins, around ${coin_in:,.0f} in total action, and an estimated ${loss:,.0f} in theoretical loss. "
        f"Friendly reality check - Real play doesn't follow a script. Some sessions will run betterm some worse. That's part of the game! "
    )

    if profile.points_mode == "coin_in":
        method = (
            "Because this game earns points from the amount you cycle through the machine, your points are fairly straightforward to estimate. "
        )
    else:
        method = (
            "Because this is a table game, Royal Caribbean does not publish a point formula, so this result is best used as a planning estimate rather than a guarantee. "
        )

    if tier_name == "Prime":
        close = "If your real goal is to unlock free casino drinks and the annual interior cruise benefit, Prime is the first big milestone. Keep in mind, this status can be earned over the course of the casino year, which runs from approx. April 1 thru March 31st. "
    elif tier_name == "Signature":
        close = "Signature is a major jump because you move into stronger annual cruise value and extra onboard perks."
    elif tier_name == "Masters":
        close = "Masters is the top level, so this is a serious high-play target rather than a casual milestone."
    else:
        close = "While this isn't a large milestone, you can check with the casino host to understand what instant certificates you will earn for this cruise based upon these points."

    return base + method + close



def playful_divider() -> None:
    st.markdown('<div class="playful-divider">$ $ $ $ $ $ $ $ $ $ $ $ $</div>', unsafe_allow_html=True)


# -----------------------------
# UI
# -----------------------------
st.title("Royal Caribbean Casino Royale")
st.caption("Choose your game, choose your point goal, and see how long it may take to get there.")


playful_divider()

selected_game = st.selectbox("Select game", list(GAME_PROFILES.keys()))
profile = GAME_PROFILES[selected_game]

average_bet = st.number_input(
    "Average bet per hand or spin ($)",
    min_value=0.01,
    value=5.0,
    step=1.0,
)

goal_label = st.selectbox("Select goal", [label for label, _ in GOAL_OPTIONS])
goal_points = dict(GOAL_OPTIONS)[goal_label]

playful_divider()

st.subheader("Editable assumptions")
col1, col2 = st.columns(2)
with col1:
    rounds_per_hour = st.number_input(
        "Rounds or hands per hour",
        min_value=1,
        value=profile.rounds_per_hour,
        step=1,
    )
with col2:
    house_edge_percent = st.number_input(
        "House edge (%)",
        min_value=0.1,
        value=round(profile.house_edge * 100, 2),
        step=0.1,
    )

results = calculate_goal_results(
    profile=profile,
    average_bet=average_bet,
    goal_points=goal_points,
    rounds_per_hour=rounds_per_hour,
    house_edge_percent=house_edge_percent,
)

tier_name = get_tier_name(goal_points)

playful_divider()

st.markdown('<div class="result-card"><div class="result-label">Approx. hours you need to play</div>'
            f'<div class="result-value">{results["required_hours"]:,.1f}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="result-card"><div class="result-label">Estimated theoretical loss</div>'
            f'<div class="result-value">${results["required_theoretical_loss"]:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="result-card">
        <div class="result-label">Estimated total action</div>
        <div class="result-value">${results['required_coin_in']:,.0f}</div>
        <div class="small-note">This is the estimated amount cycled through the game to reach your point goal.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

playful_divider()

st.subheader("Explanation")
st.write(human_explanation(selected_game, goal_points, results, profile))
st.info(profile.note)

if tier_name in TIER_BENEFITS:
    st.markdown(
        f"""
        <div class="benefit-box">
            <strong>{tier_name} benefits</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for benefit in TIER_BENEFITS[tier_name]:
        st.markdown(f"- {benefit}")

with st.expander("How the estimate is calculated"):
    st.write(
        "This tool uses your selected game, average bet, house edge, and rounds or hands per hour to estimate the amount of play needed to reach your selected point goal. "
        "This is for informational and entertainment purposes only and was created by a fellow RC guest. " 
        "It is not financial or gambling advice. Please play responsibily. "
    )


with st.expander("Official tier ranges"):
    st.markdown(
        "- Prime: 2,500 to 24,999 points\n"
        "- Signature: 25,000 to 99,999 points\n"
        "- Masters: 100,000+ points"
    )
