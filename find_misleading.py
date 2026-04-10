"""Filter misinformation claims to find ones that could cause a viewer to take the wrong action.

Usage:
    python find_misleading.py transcripts/0P4GBje7p4U_misinformation_20260409_190039.json
    python find_misleading.py transcripts/0P4GBje7p4U_misinformation_20260409_190039.json --model openai/gpt-oss-120b
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import List

from openai import OpenAI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Few-shot examples — edit this list to steer the LLM's judgment.
#
#   Positive examples  → claims that ARE misleading / actionably harmful
#   Negative examples  → claims that are NOT misleading (LLM should skip these)
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLES = [
    # ── POSITIVE (misleading & could cause wrong action) ──────────────────
    {
        "claim": "Liver tests are often the first thing that tells me which direction someone's health is going in.",
        "is_misleading": True,
        "wrong_reason": "Liver tests are not always the first indicator of health problems. Many serious liver conditions can develop without causing noticeable changes in liver enzyme levels. Additionally, other types of blood tests, such as complete blood counts or metabolic panels, are usually done before liver tests and provide early clues about a person's health status.",
        "misleading_action": "Viewer may become overly reliant on liver tests for monitoring their health and may neglect other important health indicators",
        "manipulation_tactic": "False causation — presents liver tests as the only indicator of health",
        "severity": "high",
    },
    {
        "claim": "Mucus in the stool is far more commonly associated with IBS than with anything else that's sinister.",
        "is_misleading": True,
        "wrong_reason": "A systematic review by Lacy BE et al., 2021, found that mucus in stool is a non‑specific symptom and occurs in IBS (≈30% of patients) but also in inflammatory bowel disease (≈70%) and colorectal cancer (≈40%). Thus, mucus is not more strongly associated with IBS than with other serious conditions.",
        "misleading_action": "Viewer may dismiss the symptom as IBS and not seek medical attention for something that can be fatal",
        "manipulation_tactic": "False reassurance - downplaying the seriousness of a symptom",
        "severity": "high",
    },
    {
        "claim": "The LDL story is a myth perpetuated by the pharmaceutical industry.",
        "is_misleading": True,
        "wrong_reason": "Independent replication of findings across multiple studies and drug classes, including non-industry funded research (e.g., genetic studies, meta-regression analyses).",
        "misleading_action": "Viewer stops taking statins or other cholesterol-lowering medications, increasing their risk of heart attack and stroke.",
        "manipulation_tactic": "Conspiracy theory - presents a complex scientific issue as a simple conspiracy to manipulate the public",
        "severity": "high",
    },
    {
        "claim": "Statins don't lower blood pressure.",
        "wrong_reason": "A 2018 study published in the Journal of the American College of Cardiology found that statin therapy can lead to significant reductions in blood pressure in patients with hypertension (5)",
        "is_misleading": True,
        "misleading_action": "Viewer stops taking statins or other cholesterol-lowering medications, increasing their risk of heart attack and stroke.",
        "manipulation_tactic": "Conspiracy theory - presents a complex scientific issue as a simple conspiracy to manipulate the public",
        "severity": "high",
    },
    {
        "claim": "Insulin never falls for 12-16 hours due to frequent eating and this chronic low‑grade insulin elevation is a major driver of hypertension via sodium retention.",
        "wrong_reason": "anyone that’s stepped into a hospital and seen the vital signs monitor of a patient receiving energy via IV should know this is just false",
        "is_misleading": True,
        "misleading_action": "Viewer changes their food intake timing without a possible benefit",
        "manipulation_tactic":"Absolute language 'never'",
        "severity": "medium",
    },
    {
        "claim": "Modern health care is reactive by design. We wait until somebody has a heart attack before we talk about prevention.",
        "is_misleading": True,
        "wrong_reason": "This is false - system is proactive with vaccinations, screenings, and early intervention",
        "misleading_action": "Viewer avoids or distrusts preventive doctor visits, thinking they're useless",
        "manipulation_tactic": "Fear-based hook — frames the medical system as broken to build distrust",
        "severity": "medium",
    },
    {
        "claim": "1 hour of exercise in the morning or evening can't undo 10 hours of stillness.",
        "is_misleading": True,
        "wrong_reason": "Research demonstrates that the association between sitting and mortality is *not* independent of exercise; the risk was nullified in individuals who performed ≥60 min/day of moderate‑to‑vigorous activity.",
        "misleading_action": "Viewer becomes anxious about sitting at work and may quit a desk job or damage relationships by refusing to sit with family. Furthermore, the viewer may justify avoiding strenuous exercise, thinking it's pointless",
        "manipulation_tactic": "Catastrophizing - presents sitting as an unrecoverable death sentence regardless of other habits",
        "severity": "medium",
    },
    {
        "claim": "Better metabolic health from frequent light movement decreases dementia risk.",
        "is_misleading": True,
        "wrong_reason": "Evidence suggests that strenuous exercise, and not light movement, decreases dementia risk",
        "misleading_action": "Viewer may reduce strenuous exercise, which actually have evidence for decreasing dementia risk - unlike lighter movement",
        "manipulation_tactic": "False equivalence - equating light movement with strenuous exercise",
        "severity": "medium",
    },
    # {
    #     "claim": "Blood‑pressure variability (BPV) independently doubles stroke risk in the highest quartile.",
    #     "is_misleading": True,
    #     "wrong_reason": "A systematic review (Mena L et al., \"Blood pressure variability and risk of stroke: a meta‑analysis,\" Hypertension, 2019) found a pooled relative risk of 1.20 (95 % CI 1.07‑1.34) for stroke in the highest BPV quartile, not a two‑fold increase. The association becomes non‑significant after adjusting for mean BP and antihypertensive treatment adherence.",
    #     "misleading_action": "Viewer may become anxious about normal BP fluctuations",
    #     "manipulation_tactic": "Exaggeration - inflating a modest risk increase to appear more dramatic",
    #     "severity": "medium",
    # },
    {
        "claim": "The body treats total daily energy expenditure as a constrained variable; beyond a certain activity threshold, extra exercise does not increase total calories out",
        "is_misleading": True,
        "wrong_reason": "The body does not have a maximum total daily energy expenditure. Müller et al., 2022, 'Compensatory changes in non‑exercise activity thermogenesis after exercise training' (Medicine & Science in Sports & Exercise) – found only partial compensation; participants increased total EE by ~30 % of the exercise‑induced expenditure.",
        "misleading_action": "Viewer may reduce their total exercise thinking that more execise is useless",
        "manipulation_tactic": "None",
        "severity": "medium",
    },
    {
        "claim": "Insulin resistance is the bigger driver of hypertension than sodium intake.",
        "wrong_reason": "The 2017 American Heart Association scientific statement on hypertension emphasizes excess dietary sodium as the most important modifiable risk factor for elevated blood pressure (Cook et al., Hypertension 2017)",
        "is_misleading": True,
        "misleading_action": "The viewer focuses on insulin resistance instead of their sodium intake",
        "manipulation_tactic": "None",
        "severity": "medium",
    },
    {
        "claim": "Unprocessed red meat eaten in modest amounts does not increase cardiovascular disease risk compared with people who avoid red meat entirely",
        "wrong_reason": "Large prospective cohort analyses (e.g., the EPIC study, *BMJ* 2019; 364: k4715) found a statistically significant increase in coronary heart disease risk per 100 g/day of unprocessed red meat (RR ≈ 1.15).",
        "is_misleading": True,
        "misleading_action": "Person eats read meat without knowing the risks on cardiovascular disease",
        "manipulation_tactic": "None",
        "severity": "medium"
    },
    {
        "claim": "Regular cold exposure “trains” the body to manage inflammation and therefore reduces chronic inflammation that drives age‑related disease.",
        "wrong_reason": "A randomized trial (Janský et al., 2021, *European Journal of Applied Physiology*) found no change in C‑reactive protein or IL‑6 after 6 weeks of daily 5‑minute cold showers.",
        "is_misleading": True,
        "misleading_action": "Viewer tortures themselves with cold-showers for no reason",
        "manipulation_tactic": "None",
        "severity": "medium"
    },
    # {
    #     "claim": "Consuming 25‑35 g of high‑quality protein at breakfast leads to greater muscle‑protein synthesis and better muscle‑mass preservation than the same protein eaten later in the day.",
    #     "wrong_reason": "",
    #     "is_misleading": True,
    #     "misleading_action": " If eating at breakfast doesn’t affect how much protein you eat in total, you shouldn’t be forcing yourself to eat it on breakfast",
    #     "manipulation_tactic": "None",
    #     "severity": "medium"    
    # },
    # ── NEGATIVE (not misleading — LLM should skip these) ─────────────────
    {
        "claim": "Anthocyanins can cross the blood‑brain barrier and directly protect brain tissue.",
        "wrong_reason": "Most human studies show that anthocyanins are poorly absorbed and only trace amounts are detected in plasma; animal studies suggest limited BBB penetration (e.g., Manach et al., *J Nutr* 2004; 134: 3105‑3112).",
        "is_misleading": False,
        "misleading_action": "None - the user might consume more berries. No harm done",
        "manipulation_tactic": "None",
        "severity": "low"
    },
    {
        "claim": "Ultra‑processed foods are always low in protein and fiber and high in refined carbs and seed oils",
        "wrong_reason": "The NOVA classification defines ultra‑processed foods by formulation and industrial processing, not by macronutrient composition. Many ultra‑processed products (e.g., fortified soy drinks, protein bars, legume‑based meat analogues) contain ≥15 g protein per 100 g and substantial fiber (Monteiro et al., BMJ 2019)",
        "is_misleading": False,
        "misleading_action": "None - The user likely interprets the claim as referring to junk food instead of things like protein bars.",
        "manipulation_tactic": "Absolute language",
        "severity": "low"

    },
    {
        "claim": "National food surveys in the UK have shown that we've actually been consuming fewer calories per day since the 1970s. The estimated daily calorie intake has dropped.",
        "wrong_reason": "A 2020 analysis by Poppitt et al., \"Energy intake trends in the UK\" (British Journal of Nutrition) concluded that apparent declines in self‑reported intake are attributable to increasing under‑reporting, not true reductions.",
        "is_misleading": False,
        "misleading_action": "None - this is inactionable",
        "manipulation_tactic": "None",
        "severity": "low"

    },
    {
        "claim": "Walking speed >1 m/s reduces mortality risk by 12 % for each 0.1 m/s increase.",
        "wrong_reason": "The original pooled analysis of gait speed (Studenski S et al., JAMA, 2011) reported a 9 % lower risk of mortality per 0.1 m/s increase, not 12 %. Moreover, the association is largely driven by baseline health status; after full adjustment for comorbidities the effect size drops to ≈5 %",
        "is_misleading": False,
        "misleading_action": "None - this is a slight mistake that doesn't really influence the viewer",
        "manipulation_tactic": "None",
        "severity": "low"

    },
    {
        "claim": "Blue‑zone populations achieve longevity primarily because they engage in constant low‑level activity rather than structured exercise.",
        "wrong_reason":"Willcox, D.C., et al. (2014). 'The Okinawan diet, low disease mortality, and healthy life expectancy.' Nutrition Reviews, 72(5), 273‑286. Longevity in Blue Zones is attributed to a complex mix of diet, social structure, genetics, and lifelong moderate activity, not solely low‑level movement.",
        "is_misleading": False,
        "misleading_action": "None - the viewer might walk a bit more - that seems fine",
        "manipulation_tactic": "Absolute language ('primarily')",
        "severity": "low"

    },
    {
        "claim": "Cardiorespiratory fitness (CRF) is the single strongest objective predictor of mortality, stronger than age, smoking, hypertension, cholesterol, diabetes, and genetics.",
        "is_misleading": False,
        "wrong_reason": "Multiple large cohort studies (e.g., the Cooper Center Longitudinal Study, Blair SN et al., 1989; the Copenhagen City Heart Study, Lee DC et al., 2010) demonstrate that CRF is a powerful predictor, but age remains the dominant factor (age HR≈1.07 per year). Smoking, hypertension, and LDL‑C each have hazard ratios comparable to or exceeding low CRF when modeled together.",
        "misleading_action": "Although wrong, this information is not actionable",
        "manipulation_tactic": "False hierarchy - overstating the importance of one factor while downplaying others",
        "severity": "low"
    },
]


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------
class MisleadingClaim(BaseModel):
    original_claim: str = Field(description="The verbatim claim from the misinformation file.")
    misleading_action: str = Field(description="What wrong action a viewer might take because of this claim.")
    manipulation_tactic: str = Field(description="The rhetorical tactic used, e.g. fear-based hook, false urgency, catastrophizing.")
    severity: str = Field(description="How harmful the potential wrong action is: 'low', 'medium', or 'high'.")


class MisleadingAnalysisResult(BaseModel):
    summary: str = Field(description="Brief summary of which claims were flagged and why.")
    misleading_claims: List[MisleadingClaim] = Field(description="Only claims that could cause a viewer to take the wrong action. May be empty if none qualify.")


# ---------------------------------------------------------------------------
# LLM setup & defaults
# ---------------------------------------------------------------------------
client = OpenAI(
    api_key=os.environ.get("TOGETHER_API_KEY"),
    base_url="https://api.together.xyz/v1",
)

DEFAULT_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def _build_few_shot_block() -> str:
    """Format FEW_SHOT_EXAMPLES into a readable text block for the prompt."""
    lines = []
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        lines.append(f"Example {i}:")
        lines.append(f'  Claim: "{ex["claim"]}"')
        print("claim", ex["claim"])
        if ex["is_misleading"]:
            lines.append(f"  Verdict: MISLEADING")
            lines.append(f"  Wrong reason: {ex['wrong_reason']}")
            lines.append(f"  Wrong action viewer might take: {ex['misleading_action']}")
            lines.append(f"  Manipulation tactic: {ex['manipulation_tactic']}")
            lines.append(f"  Severity: {ex['severity']}")
        else:
            lines.append(f"  Verdict: NOT MISLEADING")
            lines.append(f"  Wrong reason: {ex['wrong_reason']}")
            lines.append(f"  Wrong action viewer might take: {ex['misleading_action']}")
            lines.append(f"  Manipulation tactic: {ex['manipulation_tactic']}")
            lines.append(f"  Severity: {ex['severity']}")
        lines.append("")
    return "\n".join(lines)


def _build_claims_block(claims: list[dict]) -> str:
    """Format the claims from the misinformation file into a numbered list."""
    lines = []
    for i, c in enumerate(claims, 1):
        evidence = "; ".join(c.get("opposing_evidence", []))
        lines.append(f"{i}. Claim: \"{c['claim_checked']}\"")
        if evidence:
            lines.append(f"   Opposing evidence: {evidence}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------
def analyze_claims(claims: list[dict], model: str) -> MisleadingAnalysisResult:
    """Send claims to the LLM and get back only the misleading ones."""
    prompt = f"""You are an expert at identifying medical misinformation that could cause real harm.

Below are claims that were already flagged as potentially inaccurate. Your job is stricter:
find ONLY the claims that are **misleading enough to push a viewer toward the WRONG ACTION**.

A claim qualifies as misleading if believing it would cause a viewer to:
- Avoid beneficial medical care or preventive visits
- Start or stop a medication/supplement/habit based on false info
- Experience unnecessary anxiety that harms their career, relationships, or mental health
- Distrust their doctor or the medical system without good reason
- Spend money on unnecessary products or services

A claim does NOT qualify if:
- It is roughly accurate even if imprecise
- It is appropriately hedged ("may", "some studies suggest")
- The worst-case action is benign (e.g. eating more vegetables)

{_build_few_shot_block()}
---

CLAIMS TO EVALUATE:
{_build_claims_block(claims)}

Rules:
1. Return ONLY claims that meet the misleading threshold above.
2. If no claims qualify, return an empty list.
3. For severity: "high" = could cause direct health harm, "medium" = could cause unnecessary worry or wasted money, "low" = mildly misleading but unlikely to cause real damage."""

    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": "You are a medical misinformation analyst focused on identifying claims that could cause viewers to take harmful actions."},
            {"role": "user", "content": prompt},
        ],
        response_format=MisleadingAnalysisResult,
        temperature=0.3,
        max_tokens=50000,
    )

    result = response.choices[0].message.parsed
    print(f"  ✓ {model} flagged {len(result.misleading_claims)} misleading claim(s)")
    return result


# ---------------------------------------------------------------------------
# File-level entry point (mirrors check_claims_for_file)
# ---------------------------------------------------------------------------
def find_misleading_for_file(input_path: Path, model_override: str = None) -> Path:
    """Analyze a single _misinformation_*.json file for actionably misleading claims.

    Returns:
        Path to the written *_misleading_*.json output file.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"file not found – {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = data.get("misinformation", [])
    if not claims:
        raise ValueError(f"no misinformation claims found in {input_path.name}")

    model = model_override or DEFAULT_MODEL
    print(f"[{input_path.name}] evaluating {len(claims)} claim(s) with {model}…")

    result = analyze_claims(claims, model)

    # Build output path: {videoId}_misleading_{timestamp}.json
    stem = input_path.stem.split("_misinformation")[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = input_path.parent / f"{stem}_misleading_{timestamp}.json"

    output = {
        "source_file": input_path.name,
        "model": model,
        "misleading_claims": [c.model_dump() for c in result.misleading_claims],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"[{input_path.name}] done – {len(result.misleading_claims)} misleading → {output_path.name}")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Find claims that could mislead viewers into taking the wrong action."
    )
    parser.add_argument("filename", help="Path to a *_misinformation_*.json file")
    parser.add_argument("--model", help=f"Together AI model id (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    try:
        find_misleading_for_file(Path(args.filename), model_override=args.model)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
