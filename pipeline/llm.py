import os
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def llm_rerank(entity, candidates, clinical_note):
    candidates_text = "\n".join([
        f"{i+1}. {c['code']} — {c['description']} (similarity: {c['combined_score']})"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are an expert medical coder with deep knowledge of ICD-10-CM coding guidelines.

Clinical Note:
{clinical_note}

Medical Entity Extracted: "{entity}"

Top ICD-10-CM Candidates from vector search:
{candidates_text}

Task:
1. Select the single most clinically accurate ICD-10-CM code for the entity "{entity}" given the clinical context.
2. You MUST select a code from the numbered list above. Do not invent codes.
3. Consider the full clinical note context, not just the entity in isolation.
4. If the entity appears negated (e.g. "no evidence of", "ruled out"), respond with NEGATED in STATUS field.
5. If uncertain (e.g. "history of", "possible"), still select the best code but set STATUS to uncertain.

Respond in this EXACT format with no extra text:
SELECTED: <exact code from the list above>
REASON: <one sentence clinical reasoning>
STATUS: <affirmed|uncertain|negated>
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        )
        return parse_llm_response(response.choices[0].message.content, candidates)
    except Exception as e:
        print(f"LLM error: {e}")
        return candidates[0] if candidates else None


def parse_llm_response(response_text, candidates):
    lines = response_text.strip().split('\n')
    result = {
        "selected_code": None,
        "reason": "",
        "status": "affirmed"
    }

    for line in lines:
        if line.startswith("SELECTED:"):
            result["selected_code"] = line.replace("SELECTED:", "").strip()
        elif line.startswith("REASON:"):
            result["reason"] = line.replace("REASON:", "").strip()
        elif line.startswith("STATUS:"):
            result["status"] = line.replace("STATUS:", "").strip().lower()

    # Match selected code to candidates
    if result["selected_code"]:
        for c in candidates:
            if c["code"] == result["selected_code"]:
                c["llm_reason"] = result["reason"]
                c["llm_status"] = result["status"]
                return c

    # Fallback to top candidate
    if candidates:
        candidates[0]["llm_reason"] = result.get("reason", "")
        candidates[0]["llm_status"] = result.get("status", "affirmed")
        return candidates[0]

    return None