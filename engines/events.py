from datetime import datetime, timedelta, timezone
import re
from difflib import SequenceMatcher

# --- CONFIGURATION ---
RECENT_DAYS = 30 
MAX_DISPLAY_PER_STOCK = 3
DEDUPLICATION_THRESHOLD = 0.6  # 60% similarity means it's a duplicate

# --- 1. SOPHISTICATED PATTERN MATCHING ---
# Tuples: (Regex Pattern, Score, Category)
# Regex allows for boundary checks (\b) to avoid partial matches

PATTERNS = [
    # --- CRITICAL GOVERNANCE (highest priority) ---
    (r"\b(fraud|investigation|raid|sebi|ed probe|show cause)\b", -15, "Governance Risk"),
    (r"\b(resigns|quits|steps down)\b", -10, "Management Change"),
    (r"\b(ban|regulatory action|penalty)\b", -12, "Regulatory Hit"),

    # --- EARNINGS: THE NUANCE LAYER ---
    # Positive Nuances
    (r"\b(loss narrows|narrowed loss|turns profitable|back in black)\b", 10, "Turnaround"),
    (r"\b(profit jumps|profit surges|doubles profit|record profit)\b", 10, "Earnings Blowout"),
    (r"\b(beats estimates|beat estimates)\b", 8, "Earnings Beat"),
    
    # Negative Nuances
    (r"\b(loss widens|widened loss|slips into loss)\b", -10, "Deterioration"),
    (r"\b(profit falls|profit drops|profit declines|net profit down)\b", -10, "Earnings Miss"),
    (r"\b(misses estimates|miss estimates)\b", -8, "Earnings Miss"),
    (r"\b(margin pressure|margins contract)\b", -7, "Operational Stress"),

    # --- STRATEGIC ---
    (r"\b(order win|bag|bags order|new contract)\b", 6, "Order Book"),
    (r"\b(acquisition|acquires|buyout)\b", 5, "Expansion"),
    (r"\b(stake sale|promoter sells)\b", -5, "Insider Selling"),
    (r"\b(buyback|bonus issue|dividend)\b", 5, "Capital Return"),

    # --- ANALYST ACTION ---
    (r"\b(downgrade|cut target|sell rating)\b", -5, "Analyst Downgrade"),
    (r"\b(upgrade|raise target|buy rating)\b", 5, "Analyst Upgrade"),
]

# --- 2. NOISE PATTERNS ---
# Headlines that sound important but are usually daily market commentary
NOISE_PATTERNS = [
    r"profit booking",  # Often confused with profit fall
    r"market live", r"sensex", r"nifty", 
    r"stock to watch", r"buzzing stock", r"hot stock",
    r"technical check", r"chart check", r"levels to watch",
    r"opening bell", r"ahead of market"
]

def _parse_event_date(item) -> datetime | None:
    """Robust date parser for Yahoo Finance dictionary."""
    content = item.get("content", {})
    
    # Try pubDate (ISO format)
    pub = content.get("pubDate")
    if pub:
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except: pass
        
    # Try providerPublishTime (Timestamp)
    ts = content.get("providerPublishTime")
    if ts:
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except: pass
        
    return None

def is_duplicate(headline, existing_headlines):
    """Checks if a headline is semantically similar to one we've already processed."""
    clean_h = headline.lower()
    for existing in existing_headlines:
        clean_e = existing.lower()
        # SequenceMatcher calculates similarity ratio
        ratio = SequenceMatcher(None, clean_h, clean_e).ratio()
        if ratio > DEDUPLICATION_THRESHOLD:
            return True
    return False

def analyze_headline(headline: str, thesis_status: str) -> dict:
    text = headline.lower()
    
    # 1. Noise Filter
    if any(re.search(pat, text) for pat in NOISE_PATTERNS):
        return None 

    score = 0
    categories = set()
    matches = []

    # 2. Regex Pattern Scanning
    for pattern, weight, category in PATTERNS:
        if re.search(pattern, text):
            score += weight
            categories.add(category)
            # We don't break; a headline can be "Earnings Miss" AND "Downgrade"
    
    # 3. Fallback Keyword Scan (If no complex patterns matched)
    if score == 0:
        if any(w in text for w in ["plunge", "crash", "tumble", "slump"]):
            score = -3
            categories.add("Price Action")
        elif any(w in text for w in ["surge", "rally", "zoom", "jump"]):
            score = 3
            categories.add("Price Action")

    # 4. Construct Verdict
    if score == 0:
        return None # Skip neutral news to reduce cognitive load
        
    # Determine Primary Category (Prioritize Negative/Governance)
    if "Governance Risk" in categories: primary_cat = "Governance Risk"
    elif "Deterioration" in categories: primary_cat = "Fundamental Decay"
    elif "Earnings Blowout" in categories: primary_cat = "Earnings Blowout"
    else: primary_cat = list(categories)[0] if categories else "General"

    # 5. Contextual Intelligence
    # If the stock is already "Weakening", negative news is a confirmation signal.
    context = ""
    if score < 0:
        if thesis_status in ["Weakening", "Broken"]:
            context = "CONFIRMATION: Validates negative thesis."
        else:
            context = "WARNING: Monitor for trend change."
    elif score > 0:
        if thesis_status == "Broken":
            context = "CONTRARIAN: Potential turnaround signal?"
        else:
            context = "MOMENTUM: Reinforces growth story."

    return {
        "headline": headline,
        "category": primary_cat,
        "impact_score": score,
        "confidence_effect": context
    }

def run_events_engine(df, thesis_data, market_data):
    """
    Premium Events Engine:
    - Filters Noise (Profit Booking vs Profit Fall)
    - Deduplicates similar headlines
    - Nuanced Scoring (Loss Widens vs Loss Narrows)
    """
    results = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    for _, row in df.iterrows():
        symbol = row["symbol"]
        if row.get("instrument_type", "Equity") != "Equity":
            continue

        thesis = thesis_data.get(symbol, {})
        current_status = thesis.get("status", "Unknown")
        
        raw_news = market_data.news.get(symbol, [])
        if not raw_news: continue

        stock_events = []
        seen_headlines = []

        for item in raw_news:
            # A. Date Check
            date = _parse_event_date(item)
            if not date or date < cutoff_date: continue

            # B. Content Check
            headline = item.get("content", {}).get("title")
            if not headline: continue
            
            # C. Deduplication
            if is_duplicate(headline, seen_headlines):
                continue
            
            # D. Analysis
            analysis = analyze_headline(headline, current_status)
            if analysis:
                seen_headlines.append(headline)
                stock_events.append({
                    "symbol": symbol,
                    "headline": analysis["headline"],
                    "published": date.strftime("%Y-%m-%d"),
                    "impact": analysis["category"], # Mapped to UI Badge
                    "confidence_effect": analysis["confidence_effect"],
                    "score": analysis["impact_score"]
                })

        # E. Intelligent Sorting
        # Sort by Severity (Absolute Score) descending
        stock_events.sort(key=lambda x: abs(x["score"]), reverse=True)
        
        # Take top N most impactful events
        results.extend(stock_events[:MAX_DISPLAY_PER_STOCK])

    return results