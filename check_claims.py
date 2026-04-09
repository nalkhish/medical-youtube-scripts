"""Analyze a formatted transcript for potentially misleading medical claims.

Usage:
    python check_claims.py transcripts/oUCAkB4AMTc_formatted.json
    python check_claims.py transcripts/oUCAkB4AMTc_formatted.json --model moonshotai/Kimi-K2.5
"""
import datetime
import json
import sys
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOGETHER_API_KEY


import os
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

# 1. Define your structure using Pydantic Models
class Claim(BaseModel):
    claim_checked: str = Field(description="The specific medical claim extracted from the transcript.")
    opposing_evidence: List[str] = Field(description="List of opposing evidence from medical literature.")
    # supporting_evidence: List[str] = Field(description="List of supporting evidence from medical literature.")

class ClaimVerificationResult(BaseModel):
    analysis_summary: str = Field(description="Write a brief summary of the transcript and list the misleading claims you found.")
    # This specifically tells the enforcer: "Expect an Array of Objects here!"
    claims_checked: List[Claim] = Field(description="MUST NOT BE EMPTY. The list of claims verified.")

class ClaimWithModel(Claim):
    model: str

client = OpenAI(
    api_key=os.environ.get("TOGETHER_API_KEY"),
    base_url="https://api.together.xyz/v1",
)

DEFAULT_MODELS = [
    # Kimi is bad at following schema
    # "moonshotai/Kimi-K2.5",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    # gpt-120b is good at following schema
    "openai/gpt-oss-120b"
]



def analyze_transcript(transcript: str, title: str, model: str):
    """Call Together AI to analyze a transcript with a single model.

    Returns a list of claim dicts (without the 'model' field yet).
    """
    # url = "https://api.together.xyz/v1/chat/completions"
    # headers = {
    #     "Authorization": f"Bearer {TOGETHER_API_KEY}",
    #     "Content-Type": "application/json",
    # }
#     prompt = """You are a medical fact-checker. You will receive a transcript from a health/medical video
#     Your task is to identify any claims that could be misleading or inaccurate in the TRANSCRIPT. For each claim, provide contrary evidence AND supporting evidence from medical literature.

#     TRANSCRIPT:
#     """ + transcript + """

#     Rules:
#     1. Output the claim checks in format {claims_checked: [{claim_checked: string, contrary_evidence: [string], supporting_evidence: [string]}]}.
#     For example, 
# {
#   "claims_checked": [
#     {
#       "claim_checked": "Example claim.",
#       "contrary_evidence": ["Example contrary."],
#       "supporting_evidence": ["Example supporting."]
#     }
#   ]
# }
#     2. Output RAW JSON only. Do not use Markdown formatting. Do not wrap the output in ```json or any other code blocks. Begin your response immediately with the opening bracket {"""

    # print("analyze_transcript prompt", prompt)

    # payload = {
    #     "model": model,
    #     "messages": [
    #         {"role": "system", "content": "You are a specialized AI assistant that outputs only valid JSON conforming strictly to the requested schema."},
    #         {"role": "user", "content": prompt},
    #     ],
    #     "temperature": 0.3,
    #     "max_tokens": 30000,
    #     "response_format": {"type": "json_object"},
    # }

    # resp = requests.post(url, headers=headers, json=payload, timeout=300)
    # resp.raise_for_status()
    # result = resp.json()
    # content = result["choices"][0]["message"]["content"]
    # print("result", result)

    # try:
    #     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    #     safe_model_name = model.replace("/", "_")
    #     result_filename = f"misinformation_{timestamp}_{safe_model_name}.json"
        
    #     # save the result to a timestamped json
    #     with open(result_filename, "w", encoding="utf-8") as f:
    #         json.dump(result, f, indent=4)
    # except Exception as e:
    #     print(f"Error saving result: {e}")

    prompt = """You are a medical fact-checker. You will receive a transcript from a health/medical video
    Your task is to identify any false claims in the TRANSCRIPT. For each inaccurate claim, provide opposing evidence from medical literature.

    TRANSCRIPT:
    """ + transcript + """

    Rules:
    1. If the claim can be true, ignore it."""



    response = client.beta.chat.completions.parse(
        model=model, 
        messages=[
            {"role": "system", "content": "You are a specialized medical AI assistant."},
            {"role": "user", "content": prompt}
        ],
        response_format=ClaimVerificationResult, # Pass the Pydantic class directly!
        temperature=0.5,
        max_tokens=100000,
    )

    print("analyze_ transcript response by model", model, response)
    print("\n\n\n")

    result = response.choices[0].message.parsed
    print("analyze_transcript result by model", model, result)
    
    return result


def run_model(transcript: str, title: str, model: str):
    """Wrapper that attaches the model name to each claim dict."""
    print(f"  → analyzing with {model} …")
    try:
        claims = analyze_transcript(transcript, title, model)
        assert isinstance(claims, ClaimVerificationResult)
        claims_with_model = []
        for claim in claims.claims_checked:
            claim = ClaimWithModel(model=model, **claim.model_dump())
            claims_with_model.append(claim)
        print(f"  ✓ {model} returned {len(claims_with_model)} claim(s)")
        return claims_with_model
    except Exception as e:
        print(f"  ✗ {model} failed: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Check a formatted transcript for potentially misleading medical claims."
    )
    parser.add_argument("filename", help="Path to a *_formatted.json transcript file")
    parser.add_argument("--model", help="Together AI model id (omit to use default list)")
    args = parser.parse_args()

    if not TOGETHER_API_KEY:
        print("Error: TOGETHER_API_KEY env var not set.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.filename)
    if not input_path.exists():
        print(f"Error: file not found – {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    transcript = data.get("transcript", "")
    title = data.get("title", "")

    if not transcript.strip():
        print("Error: transcript field is empty.", file=sys.stderr)
        sys.exit(1)

    models = [args.model] if args.model else DEFAULT_MODELS
    print(f"Checking claims in {input_path.name} with {len(models)} model(s)…")

    all_claims: list[ClaimWithModel] = []
    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        futures = {
            pool.submit(run_model, transcript, title, m): m for m in models
        }
        for future in as_completed(futures):
            all_claims.extend(future.result())

    # Build output path: id_misinformation.json  (replaces _formatted.json)
    stem = input_path.stem.replace("_formatted", "")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = input_path.parent / f"{stem}_misinformation_{timestamp}.json"

    output = {"misinformation": [claim.model_dump() for claim in all_claims]}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"Done – {len(all_claims)} claim(s) written to {output_path}")


if __name__ == "__main__":
    main()
