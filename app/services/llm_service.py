"""Optional LLM Explanation Layer with Deterministic Fallback."""

import os
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import logger

try:
    import openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class LLMExplanationService:
    """Provides customer-facing and engineer-facing explanations using OpenAI or deterministic templates."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.client = None
        if self.api_key and _HAS_OPENAI:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
            except Exception as exc:
                logger.warning(f"Failed to initialize OpenAI client: {exc}")

    def generate_incident_narratives(
        self,
        request_id: str,
        category: str,
        confidence: float,
        root_cause: str,
        evidence_list: list,
        default_engineer_summary: str,
        default_customer_summary: str,
    ) -> Dict[str, str]:
        """
        Generate or refine engineer-facing and customer-facing incident summaries.
        Falls back strictly to deterministic templates when OpenAI API key is not configured.
        """
        if not self.client:
            return {
                "source": "deterministic_template",
                "engineer_summary": default_engineer_summary,
                "customer_summary": default_customer_summary,
            }

        # LLM enhancement: provide strictly factual ground truth
        facts = (
            f"Request ID: {request_id}\n"
            f"Diagnosed Category: {category} (Confidence: {confidence*100:.1f}%)\n"
            f"Root Cause: {root_cause}\n"
            f"Verified Evidence:\n" + "\n".join(f"- {e}" for e in evidence_list)
        )

        prompt = (
            "You are a Senior Product Solutions Engineer at an enterprise SaaS company. "
            "Based strictly on the verified evidence below, provide two sections:\n"
            "1. ENGINEER_SUMMARY: A crisp, forensic technical summary for internal engineers.\n"
            "2. CUSTOMER_SUMMARY: A polite, professional, non-jargon explanation for the customer integration team.\n\n"
            "Do NOT invent any facts, numbers, or unverified claims.\n\n"
            f"{facts}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            content = response.choices[0].message.content or ""

            # Parse sections if cleanly formatted
            if "CUSTOMER_SUMMARY:" in content:
                parts = content.split("CUSTOMER_SUMMARY:")
                eng = parts[0].replace("ENGINEER_SUMMARY:", "").strip()
                cust = parts[1].strip()
                return {
                    "source": f"openai_{self.model}",
                    "engineer_summary": eng or default_engineer_summary,
                    "customer_summary": cust or default_customer_summary,
                }

            return {
                "source": f"openai_{self.model}",
                "engineer_summary": content.strip(),
                "customer_summary": default_customer_summary,
            }

        except Exception as exc:
            logger.warning(f"OpenAI call failed ({exc}). Falling back to deterministic templates.")
            return {
                "source": "deterministic_template_fallback",
                "engineer_summary": default_engineer_summary,
                "customer_summary": default_customer_summary,
            }
