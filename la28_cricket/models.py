"""HTTP Client wrapper for OpenAI-compatible LLM inference servers with strict baseline sampling and dry-run support."""
from __future__ import annotations

import hashlib
import json
import random
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from la28_cricket.config import DEFAULT_ENDPOINT, DESK_ORGS, FIXED_SAMPLING_BASELINE
from la28_cricket.schema import ModelCallTelemetry


def query_remote_models(endpoint: str = DEFAULT_ENDPOINT, timeout: float = 10.0, api_key: Optional[str] = None) -> List[str]:
    """Query GET /v1/models on remote endpoint and return list of model IDs."""
    url = endpoint.rstrip("/") + "/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            models_list = data.get("data", [])
            return [m.get("id") for m in models_list if isinstance(m, dict) and "id" in m]
    except Exception as exc:
        raise RuntimeError(f"Failed to query /v1/models at {url}: {exc}") from exc


def generate_synthetic_response(model_id: str, prompt: str) -> Tuple[str, int, int]:
    """Generate deterministic synthetic text and token metrics for dry-run testing."""
    seed_str = model_id + prompt[:50]
    seed_int = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16)
    rand = random.Random(seed_int)
    desk_name = DESK_ORGS.get(model_id, f"Desk ({model_id})")
    
    if "Judge two fictional cricket broadcast candidates" in prompt:
        chosen = "A" if rand.random() > 0.4 else "B"
        score = rand.randint(7, 10)
        text = f"WINNER: {chosen}\nSCORE: {score}/10\nREASON: Strong radio drama, crisp score updates, and vivid crowd atmosphere."
    elif "End with two independent prediction calls" in prompt:
        text = (
            f"Fictional commentary by {desk_name}. South Africa bowls brilliantly in the middle overs. "
            f"The crowd roars as boundary catches are taken cleanly under lights.\n"
            f"NEXT_MATCH_PREDICTION: South Africa — {rand.randint(70, 95)}%\n"
            f"FINAL_PREDICTION: South Africa — {rand.randint(65, 90)}%"
        )
    else:
        text = (
            f"Live commentary by {desk_name}. A towering six clears the boundary fence! "
            f"The supporters wave flags frantically while the bowler returns to their mark."
        )
    
    completion_tokens = max(10, len(text.split()) * 2)
    prompt_tokens = max(15, len(prompt.split()) * 2)
    return text, completion_tokens, prompt_tokens


def call_inference_endpoint(
    model: str,
    system_prompt: str,
    user_prompt: str,
    endpoint: str = DEFAULT_ENDPOINT,
    sampling_params: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
    timeout: float = 300.0,
    api_key: Optional[str] = None,
) -> ModelCallTelemetry:
    """Call the LLM inference server via SSE streaming with strict fixed sampling baseline."""
    desk_name = DESK_ORGS.get(model, model)
    if sampling_params is None:
        sampling_params = FIXED_SAMPLING_BASELINE
    effective_sampling = {
        "temperature": sampling_params.get("temperature", 0.2),
        "top_p": sampling_params.get("top_p", 0.9),
        "seed": sampling_params.get("seed", 42),
        "presence_penalty": sampling_params.get("presence_penalty", 0),
        "frequency_penalty": sampling_params.get("frequency_penalty", 0),
        "max_tokens": sampling_params.get("max_tokens", 300),
    }

    if dry_run:
        started = time.perf_counter()
        time.sleep(0.01)  # Simulate small execution delay
        text, comp_tok, prompt_tok = generate_synthetic_response(model, user_prompt)
        elapsed = time.perf_counter() - started
        tok_per_sec = comp_tok / elapsed if elapsed > 0 else 0.0
        return ModelCallTelemetry(
            model_id=model,
            desk_name=desk_name,
            text=text,
            elapsed_s=round(elapsed, 4),
            completion_tokens=comp_tok,
            prompt_tokens=prompt_tok,
            tok_per_sec=round(tok_per_sec, 2),
            status="ok",
            endpoint=endpoint,
            attempt_count=1,
            requested_sampling=effective_sampling,
        )

    chat_url = endpoint.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **effective_sampling,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    started = time.perf_counter()
    text = ""
    completion_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None

    last_exc = None
    delay = 1.0
    attempt_count = 0

    for attempt in range(3):
        attempt_count = attempt + 1
        text = ""
        completion_tokens = None
        prompt_tokens = None
        try:
            request = urllib.request.Request(
                chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    usage = event.get("usage") or {}
                    if usage.get("completion_tokens") is not None:
                        completion_tokens = int(usage["completion_tokens"])
                    if usage.get("prompt_tokens") is not None:
                        prompt_tokens = int(usage["prompt_tokens"])
                    for choice in event.get("choices", []):
                        delta = (choice.get("delta") or {}).get("content") or ""
                        if delta:
                            text += delta
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(delay)
                delay *= 2

    elapsed = time.perf_counter() - started

    if last_exc is not None:
        return ModelCallTelemetry(
            model_id=model,
            desk_name=desk_name,
            text="",
            elapsed_s=round(elapsed, 3),
            completion_tokens=None,
            prompt_tokens=None,
            tok_per_sec=None,
            status="error",
            error=str(last_exc),
            endpoint=endpoint,
            attempt_count=attempt_count,
            requested_sampling=effective_sampling,
        )

    tok_per_sec = (completion_tokens / elapsed) if (completion_tokens and elapsed > 0) else None

    return ModelCallTelemetry(
        model_id=model,
        desk_name=desk_name,
        text=text.strip(),
        elapsed_s=round(elapsed, 3),
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        tok_per_sec=round(tok_per_sec, 2) if tok_per_sec is not None else None,
        status="ok",
        endpoint=endpoint,
        attempt_count=attempt_count,
        requested_sampling=effective_sampling,
    )
