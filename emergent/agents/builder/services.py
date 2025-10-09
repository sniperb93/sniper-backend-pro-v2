import os
import requests
from typing import Optional

# OpenAI SDK est installé si vous souhaitez un fallback
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

EMERGENT_LLM_URL = os.getenv("EMERGENT_LLM_URL", "https://api.emergent-llm.ai")


def ask_emergent_llm(prompt: str, model: str = "emergent-llm-v1", agent: Optional[str] = None, timeout: int = 15) -> Optional[str]:
    """
    Tente d'utiliser la clé universelle Emergent si disponible.
    """
    uni_key = os.getenv("EMERGENT_UNIVERSAL_KEY") or os.getenv("EMERGENT_LLM_KEY")
    if not uni_key:
        return None
    try:
        url = f"{EMERGENT_LLM_URL.rstrip('/')}/infer"
        headers = {
            "Authorization": f"Bearer {uni_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "agent": agent or "builder-agent",
            "prompt": prompt,
        }
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            return None
        data = r.json()
        return data.get("response") or data.get("text")
    except Exception:
        return None


def ask_openai(prompt: str, model: str = "gpt-5", timeout: int = 20) -> Optional[str]:
    """
    Fallback OpenAI si la clé universelle n'est pas disponible.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )
        return res.choices[0].message.content
    except Exception:
        return None


def ask_llm(prompt: str, model: Optional[str] = None, agent: Optional[str] = None) -> str:
    """
    Passerelle universelle: tente d'abord Emergent, puis OpenAI.
    """
    # 1) Essayer Emergent Universal Key
    resp = ask_emergent_llm(prompt, model or "emergent-llm-v1", agent=agent)
    if resp:
        return resp
    # 2) Fallback OpenAI si dispo
    resp = ask_openai(prompt, model or "gpt-5")
    if resp:
        return resp
    # 3) Aucun moteur disponible
    return "Aucune IA disponible. Configurez EMERGENT_UNIVERSAL_KEY ou OPENAI_API_KEY."