import yfinance as yf
from datetime import datetime, timedelta, timezone
import re

RECENT_DAYS = 14
MAX_NEWS_PER_STOCK = 3


# -----------------------------
# Date parsing (unchanged)
# -----------------------------
def _parse_event_date(item) -> datetime | None:
    """
    Parse Yahoo Finance news timestamps safely.
    Always returns timezone-aware UTC datetime.
    """
    content = item.get("content", {})

    pub = content.get("pubDate")
    if pub:
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    ts = content.get("providerPublishTime")
    if ts:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass

    return None


# -----------------------------
# News fetcher (unchanged)
# -----------------------------
def fetch_stock_news(symbol: str) -> list[dict]:
    """
    Fetches recent, relevant Yahoo Finance headlines.
    Time comparisons are UTC-safe.
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        news_items = ticker.news or []

        cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
        results = []

        for item in news_items:
            content = item.get("content", {})
            headline = content.get("title")
            if not headline:
                continue

            event_date = _parse_event_date(item)

            if event_date and event_date < cutoff:
                continue

            results.append({
                "headline": headline,
                "published": (
                    event_date.isoformat()
                    if event_date
                    else "Unverified"
                )
            })

        return results[:MAX_NEWS_PER_STOCK]

    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []


# -----------------------------
# UPDATED EVENT INTERPRETER
# -----------------------------
def run_events_engine(df, thesis_data):
    """
    Portfolio-aware news intelligence engine.
    Uses priority-based semantic rules.
    Emits informational + confidence effects only.
    """

    results = []

    # --- Priority keyword layers ---
    NEGATIVE_VERBS = {
        "slump", "slumps", "fall", "falls", "fell",
        "tumble", "tumbles", "shed", "miss", "misses",
        "decline", "declines", "loss", "drops"
    }

    LEGAL_REGULATORY = {
        "sec", "summons", "probe", "penalty", "ban",
        "lawsuit", "court", "regulator", "investigation",
        "compliance", "fraud"
    }

    POSITIVE_TERMS = {
        "beats", "strong growth", "record profit",
        "order win", "approval", "expansion",
        "surge", "deal wins"
    }

    EDITORIAL_PATTERNS = [
        r"what makes .* worthy",
        r"is .* a good investment",
        r"should you buy",
        r"analysis:"
    ]

    for _, row in df.iterrows():
        symbol = row.get("symbol")
        if row.get("instrument_type") != "Equity":
            continue

        thesis = thesis_data.get(symbol) or {}
        thesis_status = thesis.get("status", "Unknown")

        news_items = fetch_stock_news(symbol)

        for news in news_items:
            headline = news["headline"]
            text = headline.lower()

            impact = "Neutral"
            confidence_effect = "Informational"

            # -----------------------------
            # RULE 1: Editorial / opinion → Neutral
            # -----------------------------
            if any(re.search(pat, text) for pat in EDITORIAL_PATTERNS):
                impact = "Neutral"
                confidence_effect = "Informational"

            # -----------------------------
            # RULE 2: Legal / regulatory → Negative
            # -----------------------------
            elif any(k in text for k in LEGAL_REGULATORY):
                impact = "Negative"
                confidence_effect = (
                    "Increases downside risk"
                    if thesis_status in ("Weakening", "Broken")
                    else "Monitor for escalation"
                )

            # -----------------------------
            # RULE 3: Directional negative verbs dominate
            # -----------------------------
            elif any(k in text for k in NEGATIVE_VERBS):
                impact = "Negative"
                confidence_effect = (
                    "Increases downside risk"
                    if thesis_status in ("Weakening", "Broken")
                    else "Monitor for deterioration"
                )

            # -----------------------------
            # RULE 4: Positive only if clearly stated
            # -----------------------------
            elif any(k in text for k in POSITIVE_TERMS):
                impact = "Positive"
                confidence_effect = (
                    "Reinforces thesis"
                    if thesis_status == "Intact"
                    else "Short-term tailwind"
                )

            # -----------------------------
            # Default: Neutral informational
            # -----------------------------
            results.append({
                "symbol": symbol,
                "headline": headline,
                "published": news["published"],
                "impact": impact,
                "confidence_effect": confidence_effect,
                "news_detected": True,
                "time_horizon": "Short-term",
                "action_required": False
            })

    return results
