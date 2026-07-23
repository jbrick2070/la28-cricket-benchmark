"""Benchmark engine orchestrating 7-match / 140-over campaign, independent desk prediction, judging, and log emission."""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from la28_cricket.config import (
    CLIENT_DASHBOARD_HW,
    DEFAULT_ENDPOINT,
    ENDPOINT_A,
    ENDPOINT_B,
    API_KEY_A,
    API_KEY_B,
    DESK_ORGS,
    FIXED_SAMPLING_BASELINE,
    HERO_TEAM,
    INFERENCE_SERVER_HW,
    OPPONENT_VIBES,
    OVERS_PER_MATCH,
    PREFERRED_MODEL_A,
    PREFERRED_MODEL_B,
    PROMPT_VERSION,
    SCHEDULE,
    SECRET_MATCH_WINNERS,
    TEAM_CODES,
    TOTAL_MATCHES,
    TOTAL_TEAM_OVERS,
    get_surprise_for_over,
)
from la28_cricket.metrics import (
    evaluate_model_predictions,
    parse_predictions_from_text,
    calculate_commentary_quality,
    calculate_engagement_score,
    detect_hallucinations,
    calculate_prediction_stability,
)
from la28_cricket.models import call_inference_endpoint
from la28_cricket.schema import (
    CampaignSummaryRecord,
    MatchResultRecord,
    ModelCallTelemetry,
    OverEventRecord,
    PredictionRecord,
    RunMetadata,
    OverQualityMetrics,
    iso_timestamp,
)


def safe_slice(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    sliced = text[-max_chars:]
    first_space = sliced.find(" ")
    return sliced[first_space+1:] if first_space != -1 else sliced


class LA28CricketBenchmark:
    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model_a: str = PREFERRED_MODEL_A,
        model_b: str = PREFERRED_MODEL_B,
        judge_model: Optional[str] = None,
        log_path: str = "logs/la28_cricket_benchmark.jsonl",
        dry_run: bool = False,
        delay_seconds: float = 0.5,
        endpoint_a: Optional[str] = None,
        endpoint_b: Optional[str] = None,
        api_key_a: Optional[str] = None,
        api_key_b: Optional[str] = None,
        domain: str = "cricket",
    ) -> None:
        self.endpoint = endpoint
        self.endpoint_a = endpoint_a or ENDPOINT_A
        self.endpoint_b = endpoint_b or ENDPOINT_B
        self.api_key_a = api_key_a or API_KEY_A
        self.api_key_b = api_key_b or API_KEY_B
        self.model_a = model_a
        self.model_b = model_b
        self.judge_model = judge_model or model_b
        self.log_path = Path(log_path)
        self.dry_run = dry_run
        self.delay_seconds = delay_seconds
        self.domain = domain.lower()

        self.run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.all_predictions: List[PredictionRecord] = []
        self.all_telemetry: List[ModelCallTelemetry] = []
        self.all_quality_metrics: List[Dict[str, OverQualityMetrics]] = []
        self.head_to_head = {self.model_a: 0, self.model_b: 0}

    def _write_record(self, record_dict: Dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record_dict, ensure_ascii=False) + "\n")

    def run_campaign(self, max_overs_override: Optional[int] = None) -> Dict[str, Any]:
        """Execute campaign across 7 matches (140 total team overs)."""
        start_time = time.perf_counter()

        run_meta = RunMetadata(
            run_id=self.run_id,
            timestamp=iso_timestamp(),
            endpoint=self.endpoint,
            prompt_version=PROMPT_VERSION,
            sampling_baseline=FIXED_SAMPLING_BASELINE,
            inference_server_hw=INFERENCE_SERVER_HW,
            client_dashboard_hw=CLIENT_DASHBOARD_HW,
            models_configured=[self.model_a, self.model_b, self.judge_model],
            is_dry_run=self.dry_run,
        )
        self._write_record(run_meta.to_dict())

        total_target_overs = max_overs_override if max_overs_override is not None else TOTAL_TEAM_OVERS
        score = {"runs": 0, "wickets": 0, "balls": 0}
        previous_broadcast = "No previous ball: invent the opening delivery."
        
        match_index = 1
        over_in_match = 0
        total_overs_run = 0

        try:
            while total_overs_run < total_target_overs:
                total_overs_run += 1
                over_in_match += 1

                phase, opponent = SCHEDULE[min(match_index - 1, len(SCHEDULE) - 1)]
                opponent_vibe = OPPONENT_VIBES.get(opponent, "enthusiastic supporters")
                state_before = f"{score['runs']}/{score['wickets']} after {score['balls']} balls"

                cultural_guidance = (
                    "Represent teams respectfully. Use team names and flag codes accurately. "
                    "Describe fans through specific human actions (cheering, flags, scarves) "
                    "without claiming an entire country behaves identically. Do not invent accents, "
                    "sacred symbols, or national costumes."
                )

                base_prompt = (
                    f"Broadcast the next fictional cricket over as a vivid radio report.\n"
                    f"Act as an independent broadcast organization. Do not mention other organizations, "
                    f"hidden judging, or scoring rubrics.\n"
                    f"This is the {HERO_TEAM} women's road to the LA28 Olympic gold medal.\n"
                    f"Match {match_index} of {TOTAL_MATCHES}, over {over_in_match} of {OVERS_PER_MATCH}.\n"
                    f"Current Match: {HERO_TEAM} {TEAM_CODES.get(HERO_TEAM, '[?]')} vs {opponent} {TEAM_CODES.get(opponent, '[?]')}.\n"
                    f"Phase: {phase}. Opponent Spotlight: {opponent_vibe}.\n"
                    f"Surprise instruction: {get_surprise_for_over(match_index, over_in_match)}.\n"
                    f"{cultural_guidance}\n"
                    f"Current Score: {state_before}.\n"
                    f"Previous broadcast snippet: {safe_slice(previous_broadcast)}\n"
                    f"Give exactly one over (six deliveries), score update, and crowd atmosphere. Do not claim this is real news."
                )

                telemetry_list: List[ModelCallTelemetry] = []
                over_predictions: List[PredictionRecord] = []

                for model_id in (self.model_a, self.model_b):
                    desk_name = DESK_ORGS.get(model_id, model_id)
                    desk_prompt = f"You are broadcasting for {desk_name}.\n" + base_prompt

                    # Over 1: request pre-game match and tournament predictions
                    if over_in_match == 1:
                        desk_prompt += (
                            "\n\nEnd with two independent prediction calls, based on available T20 evidence:\n"
                            "NEXT_MATCH_PREDICTION: [team] — [confidence %]\n"
                            "FINAL_PREDICTION: [team] — [confidence %]\n"
                            "Do not claim to know hidden ground truth."
                        )

                    sys_prompt = (
                        "You are a live international cricket sports broadcaster. Sound like "
                        "a warm, exciting sports TV commentator. Be culturally respectful."
                    )

                    model_endpoint = self.endpoint_a if model_id == self.model_a else self.endpoint_b
                    model_api_key = self.api_key_a if model_id == self.model_a else self.api_key_b

                    t_res = call_inference_endpoint(
                        model=model_id,
                        system_prompt=sys_prompt,
                        user_prompt=desk_prompt,
                        endpoint=model_endpoint,
                        api_key=model_api_key,
                        sampling_params=FIXED_SAMPLING_BASELINE,
                        dry_run=self.dry_run,
                    )
                    telemetry_list.append(t_res)
                    self.all_telemetry.append(t_res)

                    if t_res.text:
                        preds = parse_predictions_from_text(
                            text=t_res.text,
                            model_id=model_id,
                            desk_name=desk_name,
                            match_index=match_index,
                            over_index=over_in_match,
                            timestamp=iso_timestamp(),
                        )
                        over_predictions.extend(preds)
                        self.all_predictions.extend(preds)

                # Judge call for commentary selection
                judge_sys = "You are a senior sports broadcast producer judging commentary quality."
                judge_user = (
                    f"Judge two fictional cricket commentary candidates for radio drama and accuracy.\n"
                    f"Candidate A ({self.model_a}): {telemetry_list[0].text}\n"
                    f"Candidate B ({self.model_b}): {telemetry_list[1].text}\n"
                    f"Format reply as:\nWINNER: A or B\nSCORE: 0-10\nREASON: one sentence"
                )

                judge_res = call_inference_endpoint(
                    model=self.judge_model,
                    system_prompt=judge_sys,
                    user_prompt=judge_user,
                    endpoint=self.endpoint,
                    sampling_params={"temperature": 0.1, "max_tokens": 120},
                    dry_run=self.dry_run,
                )

                winner_match = re.search(r"WINNER:\s*([AB])", judge_res.text, re.IGNORECASE)
                winner_idx = 0 if (winner_match and winner_match.group(1).upper() == "A") else 1
                chosen_telemetry = telemetry_list[winner_idx]
                chosen_text = chosen_telemetry.text if chosen_telemetry.text else telemetry_list[0].text

                self.head_to_head[chosen_telemetry.model_id] += 1

                # Update score state
                score["balls"] += 6
                # More strict score parsing to avoid overs/economy false positives
                found = re.search(r"(?<!over\s)(?<!\.)\b(\d{1,3})\s*/\s*([0-9]|10)\b", chosen_text, re.IGNORECASE)
                if found:
                    score["runs"] = int(found.group(1))
                    score["wickets"] = int(found.group(2))
                else:
                    score["runs"] += max(2, len(chosen_text.split()) // 20)

                # Compute and store quality metrics
                quality_metrics: Dict[str, OverQualityMetrics] = {}
                for t_res in telemetry_list:
                    cqi = calculate_commentary_quality(t_res.text) if t_res.text else 0
                    eng = calculate_engagement_score(t_res.text) if t_res.text else 0
                    hallucinations = detect_hallucinations(t_res.text, state_before) if t_res.text else []
                    # Filter predictions by this model, match and over
                    model_preds = [p for p in self.all_predictions if p.model_id == t_res.model_id and p.match_index == match_index]
                    stability = calculate_prediction_stability(model_preds) if model_preds else 0.0
                    quality_metrics[t_res.model_id] = OverQualityMetrics(
                        cqi_score=cqi,
                        engagement_score=eng,
                        hallucination_flags=hallucinations,
                        prediction_stability=stability,
                    )
                self.all_quality_metrics.append(quality_metrics)

                cqi_winner = quality_metrics[chosen_telemetry.model_id].cqi_score
                print(f"Match {match_index} Over {over_in_match} | Score: {score['runs']}/{score['wickets']} | Winner: {chosen_telemetry.desk_name} | CQI: {cqi_winner}")

                # Record over log event
                over_record = OverEventRecord(
                    timestamp=iso_timestamp(),
                    run_id=self.run_id,
                    match_index=match_index,
                    over_index=over_in_match,
                    phase=phase,
                    hero_team=HERO_TEAM,
                    opponent_team=opponent,
                    state_before=state_before,
                    telemetry=telemetry_list,
                    predictions=over_predictions,
                    judge_model=self.judge_model,
                    judge_verdict=judge_res.text,
                    judge_elapsed_s=judge_res.elapsed_s,
                    winner_model=chosen_telemetry.model_id,
                    state_after=score.copy(),
                    quality_metrics=quality_metrics,
                )
                self._write_record(over_record.to_dict())

                previous_broadcast = chosen_text

                # Check if match completed (20 overs reached)
                if over_in_match >= OVERS_PER_MATCH:
                    actual_winner = SECRET_MATCH_WINNERS[match_index - 1]
                    match_preds = [p for p in self.all_predictions if p.match_index == match_index]
                    eval_summary = evaluate_model_predictions(match_preds, [actual_winner])

                    match_rec = MatchResultRecord(
                        run_id=self.run_id,
                        timestamp=iso_timestamp(),
                        match_index=match_index,
                        phase=phase,
                        opponent=opponent,
                        actual_winner=actual_winner,
                        predictions_evaluation=eval_summary,
                    )
                    self._write_record(match_rec.to_dict())

                    match_index += 1
                    over_in_match = 0
                    score = {"runs": 0, "wickets": 0, "balls": 0}
                    previous_broadcast = "New fictional innings: invent the opening delivery."

                if self.delay_seconds > 0:
                    time.sleep(self.delay_seconds)

        except KeyboardInterrupt:
            print("\nCampaign interrupted! Saving partial summary...")
        finally:
            elapsed_total = time.perf_counter() - start_time
            metrics_eval = evaluate_model_predictions(self.all_predictions, SECRET_MATCH_WINNERS)

            # Aggregate new metrics
            model_quality_aggregates = {self.model_a: {"cqi": [], "eng": [], "hal": 0, "stab": []},
                                        self.model_b: {"cqi": [], "eng": [], "hal": 0, "stab": []}}
            for over_qm in self.all_quality_metrics:
                for mid, m in over_qm.items():
                    if mid not in model_quality_aggregates:
                        model_quality_aggregates[mid] = {"cqi": [], "eng": [], "hal": 0, "stab": []}
                    model_quality_aggregates[mid]["cqi"].append(m.cqi_score)
                    model_quality_aggregates[mid]["eng"].append(m.engagement_score)
                    model_quality_aggregates[mid]["hal"] += len(m.hallucination_flags)
                    if m.prediction_stability > 0:
                        model_quality_aggregates[mid]["stab"].append(m.prediction_stability)

            for mid, stats in model_quality_aggregates.items():
                if mid not in metrics_eval:
                    metrics_eval[mid] = {}
                cqi_list = stats["cqi"]
                eng_list = stats["eng"]
                stab_list = stats["stab"]
                metrics_eval[mid]["avg_cqi_score"] = round(sum(cqi_list)/len(cqi_list), 1) if cqi_list else 0.0
                metrics_eval[mid]["avg_engagement_score"] = round(sum(eng_list)/len(eng_list), 1) if eng_list else 0.0
                metrics_eval[mid]["total_hallucinations"] = stats["hal"]
                metrics_eval[mid]["avg_prediction_stability"] = round(sum(stab_list)/len(stab_list), 2) if stab_list else 0.0
                total_judged = self.head_to_head.get(self.model_a, 0) + self.head_to_head.get(self.model_b, 0)
                h2h_wins = self.head_to_head.get(mid, 0)
                metrics_eval[mid]["head_to_head_wins"] = h2h_wins
                metrics_eval[mid]["head_to_head_win_pct"] = round(h2h_wins / total_judged * 100, 1) if total_judged > 0 else 0.0

            campaign_rec = CampaignSummaryRecord(
                run_id=self.run_id,
                timestamp=iso_timestamp(),
                total_matches=min(match_index, TOTAL_MATCHES),
                total_overs=total_overs_run,
                total_wall_clock_s=round(elapsed_total, 2),
                metrics_per_model=metrics_eval,
                is_dry_run=self.dry_run,
            )
            self._write_record(campaign_rec.to_dict())

            return campaign_rec.to_dict()
