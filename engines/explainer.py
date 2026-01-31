import boto3
import json
import concurrent.futures
from botocore.exceptions import ClientError

# --- AWS CONFIGURATION ---
REGION_NAME = "us-east-1" 
MODEL_ID = "amazon.nova-lite-v1:0"

def _invoke_bedrock(prompt: str) -> str:
    """
    Send prompts to AWS Bedrock using the unified 'Converse' API.
    """
    client = boto3.client("bedrock-runtime", region_name=REGION_NAME)
    
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    inference_config = {"maxTokens": 300, "temperature": 0.3, "topP": 0.9}

    try:
        response = client.converse(
            modelId=MODEL_ID,
            messages=messages,
            inferenceConfig=inference_config
        )
        return response['output']['message']['content'][0]['text'].strip()

    except ClientError as e:
        return "⚠️ AI Error: Check AWS Bedrock Model Access."
    except Exception as e:
        return f"System Error: {str(e)}"

def explain_holding(symbol: str, data: dict) -> str:
    """
    Explains the 'Deep Dive' row with STOCK-SPECIFIC context.
    """
    # 1. Extract Richer Context
    action = data['advisory']['action']
    reason = data['advisory']['rationale'] # The technical reason
    sector = data['meta'].get('sector', 'Unknown Sector')
    
    # 2. Dynamic Prompting based on Action
    if action == "EXIT":
        task = f"Explain why selling this {sector} stock is necessary. Reference the specific issue: '{reason}'."
    elif action == "REPLACE":
        task = f"Explain why swapping this {sector} stock is smart. Reference the inefficiency: '{reason}'."
    else:
        task = f"Explain the current status of this {sector} stock based on: '{reason}'."

    prompt = f"""
    You are a cynical Wall Street Analyst explaining to CEO. 
    {task}
    
    Rules:
    1. Mention the ticker {symbol} and its sector ({sector}).
    2. BE SPECIFIC. Do not use generic analogies like "broken engine" or "faulty machine".
    3. Use financial tone (e.g., "capital efficiency", "structural headwinds", "valuation mismatch").
    4. Max 25 words.
    
    Explanation:
    """
    return _invoke_bedrock(prompt)

def explain_quant_metrics(optimization_data: dict, stress_data: dict) -> dict:
    """
    Translates Quant Lab results.
    """
    # Optimization Explanation
    if optimization_data and "metrics" in optimization_data:
        sharpe = optimization_data["metrics"].get("sharpe_ratio", 0)
        opt_prompt = f"""
        Explain this portfolio metric to a client: "Sharpe Ratio {sharpe:.2f}".
        Context: >1 is good, >2 is excellent. It measures return per unit of risk.
        Max 20 words. No analogies.
        """
        opt_text = _invoke_bedrock(opt_prompt)
    else:
        opt_text = "Data unavailable."
    
    # Stress Test Explanation
    if stress_data and "metrics" in stress_data:
        worst_case = stress_data["metrics"].get("worst_case_1y", 0)
        stress_prompt = f"""
        Explain this risk to CEO: "95% Worst Case loss is down to {worst_case}".
        Context: This is the 'Value at Risk'.
        Max 20 words. Be direct.
        """
        stress_text = _invoke_bedrock(stress_prompt)
    else:
        stress_text = "Data unavailable."
    
    return {"optimization": opt_text, "stress_test": stress_text}

def batch_explain_holdings(df, final_output):
    """
    Uses THREADING to fetch all explanations in parallel (Fast).
    """
    explanations = {}
    holdings_map = {h['symbol']: h for h in final_output['holdings']}
    
    # Identify stocks that actually need explanation (Active Actions + Top Holdings)
    # We increase the limit since threading makes it fast
    target_symbols = []
    
    # 1. Priority: Actions
    for sym, h in holdings_map.items():
        if h['advisory']['action'] in ["EXIT", "REPLACE", "TRIM", "WATCH"]:
            target_symbols.append(sym)
            
    # 2. Priority: Top 10 Weights
    sorted_holdings = df.sort_values("weight_pct", ascending=False)["symbol"].tolist()
    for sym in sorted_holdings[:10]:
        if sym not in target_symbols:
            target_symbols.append(sym)
            
    # 3. Parallel Execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {
            executor.submit(explain_holding, sym, holdings_map[sym]): sym 
            for sym in target_symbols if sym in holdings_map
        }
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            sym = future_to_symbol[future]
            try:
                explanations[sym] = future.result()
            except Exception as e:
                explanations[sym] = "Insight unavailable."
                
    return explanations