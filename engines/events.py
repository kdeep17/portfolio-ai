from datetime import datetime, timedelta, timezone
import re

# Constants
RECENT_DAYS = 30 
MAX_DISPLAY = 3

# --- 1. PRECISE PHRASE MATCHING (Higher Priority) ---
# We check these first. They override single keywords.
CRITICAL_PHRASES = {
    # NEGATIVE PHRASES
    "profit fall": -10, "profit drop": -10, "profit decline": -10, "net loss": -10,
    "revenue miss": -8, "sales miss": -8, "margin pressure": -8, "margin contract": -8,
    "downgrade": -8, "target cut": -5, "sell rating": -8,
    "high cost": -5, "softer demand": -5, "weak demand": -5,
    "regulatory action": -10, "show cause": -10, "ban": -10,
    
    # POSITIVE PHRASES
    "record profit": 10, "profit jump": 10, "profit surge": 10, "net profit up": 10,
    "revenue beat": 8, "sales beat": 8, "margin expand": 8,
    "upgrade": 8, "target raise": 5, "buy rating": 8,
    "order win": 8, "new contract": 8, "acquisition": 5, "bonus issue": 5
}

# --- 2. SINGLE KEYWORD FALLBACKS (Lower Priority) ---
# Only used if no specific phrase is found.
NEGATIVE_KEYWORDS = {
    "slump", "plunge", "tumble", "crash", "misses", "losses", 
    "investigation", "fraud", "default", "bankruptcy"
}

POSITIVE_KEYWORDS = {
    "surge", "rally", "outperform", "bull", "dividend", "buyback"
}

NOISE_PATTERNS = [
    r"market live", r"sensex", r"nifty", r"share price", 
    r"buy or sell", r"target price", r"stock to watch",
    r"ahead of market", r"opening bell", r"buzzing stocks",
    r"technical check", r"chart check"
]


def _parse_event_date(item) -> datetime | None:
    content = item.get("content", {})
    pub = content.get("pubDate")
    if pub:
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except: pass
    ts = content.get("providerPublishTime")
    if ts:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except: pass
    return None


def classify_news_item(headline: str, thesis_status: str) -> dict:
    text = headline.lower()
    
    # 1. Noise Filter
    if any(re.search(pat, text) for pat in NOISE_PATTERNS):
        return None 

    score = 0
    matches = []

    # 2. Phrase Matching (Weighted)
    for phrase, weight in CRITICAL_PHRASES.items():
        if phrase in text:
            score += weight
            matches.append(phrase)

    # 3. Keyword Matching (Only if score is weak/zero)
    if score == 0:
        for word in NEGATIVE_KEYWORDS:
            if word in text:
                score -= 5
                matches.append(word)
        
        for word in POSITIVE_KEYWORDS:
            if word in text:
                score += 5
                matches.append(word)

    # 4. Categorization based on Net Score
    if score <= -8:
        category = "Material Negative"
        context = "Fundamental deterioration detected"
    elif score < 0:
        category = "Negative Sentiment"
        context = "Short-term pressure"
    elif score >= 8:
        category = "Material Positive"
        context = "Fundamental catalyst detected"
    elif score > 0:
        category = "Positive Sentiment"
        context = "Momentum tailwind"
    else:
        # If neutral, we skip it to reduce noise in the dashboard
        return None

    # Context Contextualization (Adjust urgency based on Thesis)
    if score < 0 and thesis_status in ["Weakening", "Broken"]:
        context = f"CRITICAL: Validates downside ({', '.join(matches)})"
    
    return {
        "headline": headline,
        "category": category,
        "impact_score": score,
        "context": context
    }


def run_events_engine(df, thesis_data, market_data):
    results = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    for _, row in df.iterrows():
        symbol = row["symbol"]
        if row.get("instrument_type") != "Equity":
            continue

        thesis = thesis_data.get(symbol, {})
        current_status = thesis.get("status", "Unknown")
        
        raw_news = market_data.news.get(symbol, [])
        if not raw_news: continue

        valid_events = []
        for item in raw_news:
            date = _parse_event_date(item)
            if not date or date < cutoff_date: continue

            headline = item.get("content", {}).get("title")
            if not headline: continue

            analysis = classify_news_item(headline, current_status)
            if analysis:
                valid_events.append({
                    "symbol": symbol,
                    "headline": analysis["headline"],
                    "published": date.strftime("%Y-%m-%d"),
                    "impact": analysis["category"],
                    "confidence_effect": analysis["context"],
                    "score": analysis["impact_score"]
                })

        # Sort by Absolute Impact (Biggest news first)
        valid_events.sort(key=lambda x: abs(x["score"]), reverse=True)
        results.extend(valid_events[:MAX_DISPLAY])

    return results