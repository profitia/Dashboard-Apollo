#!/usr/bin/env python3
"""
Run Continuation — pipeline generujący wiadomości kontynuacyjne.

Orchestracja:
1. Wczytuje profile engagement kontaktów
2. Buduje engagement context per kontakt
3. Router decyduje o trybie (continuation mode)
4. Continuation Writer generuje wiadomość
5. Zapisuje wyniki

Feature-flagged: wymaga CONTINUATION_MODE_ENABLED = True
lub --force w CLI.

Użycie:
    python src/pipelines/run_continuation.py --config configs/continuation_example.yaml
    python src/pipelines/run_continuation.py --contacts data/contact_engagement/ --force
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

# Setup paths
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
for _d in (_ROOT_DIR, _SRC_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from core.contact_engagement_tracker import load_engagement_profile, load_all_profiles
from core.contact_engagement_context import build_engagement_context
from core.engagement_llm_summarizer import generate_context_summary
from core.reengagement_router import (
    route_contact,
    EngagementDecision,
    ROUTER_ENABLED,
)
from core.angle_tracker import suggest_next_angles, build_angle_summary
from core.continuation_writer import (
    generate_continuation_message,
    CONTINUATION_MODE_ENABLED,
)

try:
    from run_campaign import load_context_files
except ImportError:
    def load_context_files(base_dir):
        return {}

log = logging.getLogger(__name__)

# Decisions that trigger continuation generation
_CONTINUATION_DECISIONS = {
    EngagementDecision.SEND_REENGAGEMENT,
    EngagementDecision.SEND_CONTINUATION,
}


def run_continuation_pipeline(
    profiles: list[dict] | None = None,
    config: dict | None = None,
    base_dir: str = "",
    force: bool = False,
) -> dict:
    """
    Uruchamia pipeline kontynuacyjny.

    Args:
        profiles: lista profili engagement (jeśli None, wczytuje z dysku)
        config: konfiguracja (opcjonalna)
        base_dir: root projektu
        force: pomija feature flag check

    Returns:
        dict z wynikami:
        {
            "timestamp": "...",
            "total_contacts": N,
            "routed_for_continuation": N,
            "messages_generated": N,
            "skipped": N,
            "results": [...],
            "router_decisions": [...],
        }
    """
    base_dir = base_dir or _ROOT_DIR
    config = config or {}

    if not force and not CONTINUATION_MODE_ENABLED:
        log.warning("CONTINUATION_MODE_ENABLED = False. Use --force to override.")
        return {"error": "Continuation mode disabled", "results": []}

    # Load profiles
    if profiles is None:
        profiles = load_all_profiles()
    log.info("Continuation pipeline: %d profiles loaded", len(profiles))

    # Load context files
    context_files = load_context_files(base_dir)

    # Enable router for this run
    import core.reengagement_router as rr
    old_flag = rr.ROUTER_ENABLED
    rr.ROUTER_ENABLED = True

    timestamp = datetime.now().isoformat()
    results = []
    router_decisions = []
    generated = 0
    skipped = 0

    for profile in profiles:
        contact = {
            "email": profile.get("contact_email", ""),
            "first_name": profile.get("contact_name", "").split()[0] if profile.get("contact_name") else "",
            "last_name": " ".join(profile.get("contact_name", "").split()[1:]) if profile.get("contact_name") else "",
            "title": profile.get("contact_title", ""),
            "company": profile.get("company_name", ""),
            "company_name": profile.get("company_name", ""),
        }

        # Build engagement context
        eng_context = build_engagement_context(contact, profile)

        # Generate LLM summary
        eng_context["llm_context_summary"] = generate_context_summary(eng_context)

        # Route
        router_config = {
            "cooldown_days": config.get("cooldown_days", 14),
            "max_campaigns": config.get("max_campaigns", 5),
        }
        decision = route_contact(eng_context, router_config)

        router_decisions.append({
            "contact_email": contact["email"],
            "contact_name": profile.get("contact_name", ""),
            "current_status": eng_context.get("current_status", ""),
            "decision": decision["decision"],
            "reason": decision["reason"],
            "continuation_mode": decision.get("continuation_mode"),
            "recommended_angle": decision.get("recommended_angle"),
        })

        # Skip if not routed for continuation
        if decision["decision"] not in _CONTINUATION_DECISIONS:
            skipped += 1
            continue

        # Get continuation mode from router
        cont_mode = decision.get("continuation_mode", "soft_reengagement")

        # Get recommended angle
        angle_suggestions = suggest_next_angles(profile, max_suggestions=1)
        recommended_angle = None
        if angle_suggestions:
            recommended_angle = angle_suggestions[0]
        elif decision.get("recommended_angle"):
            recommended_angle = {
                "angle_id": decision["recommended_angle"],
                "label_pl": decision["recommended_angle"],
                "reason": "router_recommendation",
            }

        # Generate continuation message
        message = generate_continuation_message(
            contact=contact,
            engagement_context=eng_context,
            continuation_mode=cont_mode,
            recommended_angle=recommended_angle,
            context_files=context_files,
            config=config,
            base_dir=base_dir,
        )

        results.append({
            "contact_email": contact["email"],
            "contact_name": profile.get("contact_name", ""),
            "continuation_mode": cont_mode,
            "router_decision": decision,
            "message": message,
        })
        generated += 1

    # Restore router flag
    rr.ROUTER_ENABLED = old_flag

    output = {
        "timestamp": timestamp,
        "total_contacts": len(profiles),
        "routed_for_continuation": generated,
        "messages_generated": generated,
        "skipped": skipped,
        "results": results,
        "router_decisions": router_decisions,
    }

    log.info(
        "Continuation pipeline done: %d profiles, %d messages, %d skipped",
        len(profiles), generated, skipped,
    )
    return output


def save_continuation_output(output: dict, output_dir: str | None = None):
    """Zapisuje wyniki pipeline do plików JSON."""
    if output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(_ROOT_DIR, "outputs", "runs", f"continuation_{ts}")
    os.makedirs(output_dir, exist_ok=True)

    # Full output
    with open(os.path.join(output_dir, "continuation_output.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Router decisions
    with open(os.path.join(output_dir, "router_decisions.json"), "w", encoding="utf-8") as f:
        json.dump(output.get("router_decisions", []), f, ensure_ascii=False, indent=2)

    # Individual messages
    for i, result in enumerate(output.get("results", []), 1):
        msg_path = os.path.join(output_dir, f"continuation_message_{i}.json")
        with open(msg_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    log.info("Continuation output saved to: %s", output_dir)
    return output_dir


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Run Continuation Pipeline")
    parser.add_argument("--config", type=str, help="YAML config file")
    parser.add_argument("--force", action="store_true", help="Force run even if feature flag is off")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = {}
    if args.config:
        try:
            import yaml
            with open(args.config, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as exc:
            log.warning("Config load failed: %s", exc)

    output = run_continuation_pipeline(
        config=config,
        base_dir=_ROOT_DIR,
        force=args.force,
    )
    save_continuation_output(output, args.output_dir)

    print(f"\nContinuation pipeline complete:")
    print(f"  Total contacts: {output['total_contacts']}")
    print(f"  Messages generated: {output['messages_generated']}")
    print(f"  Skipped: {output['skipped']}")


if __name__ == "__main__":
    main()
