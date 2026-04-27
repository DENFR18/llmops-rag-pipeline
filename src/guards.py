from dataclasses import dataclass

from llm_guard.input_scanners import PromptInjection
from llm_guard.output_scanners import Anonymize
from llm_guard.vault import Vault


@dataclass
class GuardResult:
    safe: bool
    sanitized: str
    reason: str | None = None
    score: float = 0.0


class PromptGuard:
    """Wraps LLM Guard scanners with a stable interface.

    Input: blocks prompt injection attempts.
    Output: redacts PII (emails, phone numbers, names, etc.) before returning.
    """

    def __init__(self, injection_threshold: float = 0.5):
        self._vault = Vault()
        self._injection = PromptInjection(threshold=injection_threshold)
        self._anonymize = Anonymize(vault=self._vault)

    def check_input(self, prompt: str) -> GuardResult:
        sanitized, is_valid, risk_score = self._injection.scan(prompt)
        return GuardResult(
            safe=bool(is_valid),
            sanitized=sanitized,
            reason=None if is_valid else "prompt_injection_detected",
            score=float(risk_score),
        )

    def redact_output(self, prompt: str, output: str) -> GuardResult:
        sanitized, is_valid, risk_score = self._anonymize.scan(prompt, output)
        return GuardResult(
            safe=bool(is_valid),
            sanitized=sanitized,
            reason=None if is_valid else "pii_redacted",
            score=float(risk_score),
        )
