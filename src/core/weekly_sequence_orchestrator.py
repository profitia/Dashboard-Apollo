"""
Apollo Weekly Sequence Orchestrator — nowy docelowy model wysyłki.

Model: 1 tygodniowa kampania / 1 sekwencja Apollo / wielu kontaktów / różne treści per kontakt.

Zastępuje stary model 1 kontakt = 1 sekwencja.

Merge tags w template'ach:
    Subject: {{sg_email_step_N_subject}}
    Body:    {{sg_email_step_N_body}}

Flow:
    1. Pipeline generuje outreach_pack per kontakt (subject + body × 3 steps)
    2. sync_batch_custom_fields() → ustawia 6 pól na kontaktach w Apollo
    3. create_weekly_sequence() → tworzy sekwencję + steps + templates z merge tagami
    4. preflight_batch() → walidacja kontaktów
    5. enroll_batch() → enrollment kontaktów do sekwencji
    6. activate() → aktywacja sekwencji + approve touches
"""

import logging
import os
import time
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

# ============================================================
# Merge tag templates — potwierdzona składnia Apollo
# ============================================================
# Od 2026-04-20: body = {{sg_email_step_N_body}}{{pl_signature_tu}}
# Podpis jest w osobnym custom field (wspólny dla wszystkich stepów).

# Step 1: body + osobny podpis (brak thread)
# Steps 2-3: podpis jest embedded w body PRZED thread (nie ma {{pl_signature_tu}})
MERGE_TAG_TEMPLATES = {
    1: {
        "subject": "{{sg_email_step_1_subject}}",
        "body_html": "{{sg_email_step_1_body}}{{pl_signature_tu}}",
    },
    2: {
        "subject": "{{sg_email_step_2_subject}}",
        "body_html": "{{sg_email_step_2_body}}",
    },
    3: {
        "subject": "{{sg_email_step_3_subject}}",
        "body_html": "{{sg_email_step_3_body}}",
    },
}


def _get_apollo_client():
    """Lazy import ApolloClient."""
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    integracje_dir = os.path.join(root_dir, "Integracje")
    if integracje_dir not in sys.path:
        sys.path.insert(0, integracje_dir)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(integracje_dir, ".env"))
    from apollo_client import ApolloClient
    return ApolloClient()


def generate_sequence_name(
    campaign_type: str = "Standard",
    market: str = "PL",
    week: int | None = None,
    year: int | None = None,
    suffix: str = "",
) -> str:
    """
    Generuje nazwę sekwencji tygodniowej wg konwencji.

    Format: W{week}-{year}-{campaign_type}-{market}[-suffix]
    Przykład: W20-2026-Standard-PL

    Args:
        campaign_type: typ kampanii (Standard, ArticleTriggered, CSVImport, itp.)
        market: rynek (PL, EN)
        week: numer tygodnia (domyślnie: bieżący)
        year: rok (domyślnie: bieżący)
        suffix: opcjonalny suffix (np. "test", "v2")
    """
    now = datetime.now()
    if week is None:
        week = now.isocalendar()[1]
    if year is None:
        year = now.year

    name = f"W{week:02d}-{year}-{campaign_type}-{market}"
    if suffix:
        name += f"-{suffix}"
    return name


def sync_batch_custom_fields(
    contacts_with_packs: list[dict],
) -> dict[str, Any]:
    """
    Ustawia custom fields (6 pól sg_email_step_* + 1 pole pl_signature_tu) na kontaktach w Apollo.

    Od 2026-04-20: body pola zawierają HTML BEZ podpisu.
    Podpis jest w osobnym polu pl_signature_tu (wspólny dla wszystkich stepów).

    Dla każdego kontaktu:
    1. Szuka kontaktu w Apollo po email
    2. Mapuje outreach_pack → 6 custom fields (body_html_nosig)
    3. Dodaje pl_signature_tu z standalone signature HTML
    4. PATCH kontaktu z typed_custom_fields

    Args:
        contacts_with_packs: lista dict-ów, każdy z:
            - email: str
            - outreach_pack: dict z email_1, follow_up_1, follow_up_2

    Returns:
        dict z:
        - synced: int — ile kontaktów zsynchronizowano
        - failed: int
        - results: list[dict] per kontakt
        - contact_map: dict {email: {contact_id, custom_field_values}}
    """
    from core.apollo_campaign_sync import outreach_pack_to_custom_fields, get_signature_field_name
    from core.email_signature import SIGNATURE_STANDALONE_HTML

    client = _get_apollo_client()
    results = []
    contact_map = {}

    signature_field = get_signature_field_name()

    for item in contacts_with_packs:
        email = item["email"]
        outreach_pack = item["outreach_pack"]

        # Mapuj pack na 6 pól (body_html_nosig)
        field_values = outreach_pack_to_custom_fields(outreach_pack)
        if not field_values:
            results.append({"email": email, "status": "error", "reason": "no_fields_mapped"})
            continue

        # Dodaj pole podpisu
        field_values[signature_field] = SIGNATURE_STANDALONE_HTML

        # Szukaj kontaktu w Apollo
        try:
            contact = client.search_contact(email)
            if not contact:
                results.append({"email": email, "status": "error", "reason": "contact_not_found"})
                continue
            contact_id = contact["id"]
        except Exception as exc:
            results.append({"email": email, "status": "error", "reason": f"search_failed: {exc}"})
            continue

        # Zapisz custom fields
        try:
            client.update_contact_custom_fields(contact_id, field_values)
            results.append({
                "email": email,
                "status": "success",
                "contact_id": contact_id,
                "fields_count": len(field_values),
            })
            contact_map[email] = {
                "contact_id": contact_id,
                "custom_field_values": field_values,
                "apollo_contact": contact,
            }
            log.info("Custom fields synced: %s → %d fields", email, len(field_values))
        except Exception as exc:
            results.append({
                "email": email,
                "status": "error",
                "reason": f"update_failed: {exc}",
                "contact_id": contact_id,
            })

        # Rate limiting
        time.sleep(0.3)

    synced = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "error")

    log.info("Batch custom fields sync: %d synced, %d failed out of %d",
             synced, failed, len(contacts_with_packs))

    return {
        "synced": synced,
        "failed": failed,
        "results": results,
        "contact_map": contact_map,
    }


def create_weekly_sequence(
    sequence_name: str,
    cadence: list[int] | None = None,
) -> dict[str, Any]:
    """
    Tworzy sekwencję tygodniową w Apollo z merge tag templates.

    Steps:
    1. POST /emailer_campaigns → create inactive sequence
    2. POST /emailer_steps × 3 → create steps with cadence
    3. PUT /emailer_templates × 3 → set merge tag templates

    Args:
        sequence_name: nazwa sekwencji (np. "W20-2026-Standard-PL")
        cadence: lista wait_time w minutach [0, 2880, 2880] (opcjonalny override)

    Returns:
        dict z:
        - sequence_id: str
        - sequence_name: str
        - steps: list[dict] z step_id, template_id, position
        - status: "created" | "error"
    """
    from core.apollo_campaign_sync import get_sequence_cadence

    if cadence is None:
        cadence = get_sequence_cadence()

    client = _get_apollo_client()

    # 1. Utwórz sekwencję
    try:
        seq = client.create_sequence(name=sequence_name, active=False)
        sequence_id = seq["id"]
        log.info("Created sequence: %s (id=%s)", sequence_name, sequence_id)
    except Exception as exc:
        log.error("Failed to create sequence '%s': %s", sequence_name, exc)
        return {"status": "error", "reason": f"create_failed: {exc}"}

    # 2. Utwórz 3 stepy z cadence
    steps = []
    for position, wait_minutes in enumerate(cadence, start=1):
        try:
            step = client.create_sequence_step(
                sequence_id=sequence_id,
                wait_time_minutes=wait_minutes,
                position=position,
            )
            steps.append({
                "position": position,
                "step_id": step["id"],
                "wait_time_minutes": wait_minutes,
            })
            log.info("Created step %d: wait=%d min", position, wait_minutes)
        except Exception as exc:
            log.error("Failed to create step %d: %s", position, exc)
            return {
                "status": "error",
                "reason": f"step_{position}_failed: {exc}",
                "sequence_id": sequence_id,
            }

    time.sleep(1)

    # 3. Pobierz templates (auto-created z steps) i ustaw merge tagi
    #    WAŻNE: mapowanie przez step→touch→template, NIE przez sortowanie ID!
    #    Apollo nie gwarantuje, że template IDs sortują się w kolejności step positions.
    try:
        seq_data = client.get_sequence_details(sequence_id)
        all_templates = seq_data.get("emailer_templates", [])
        all_touches = seq_data.get("emailer_touches", [])
        all_steps = seq_data.get("emailer_steps", [])

        # Buduj mapę: step_id → touch → template_id
        touch_by_step = {t["emailer_step_id"]: t for t in all_touches if t.get("emailer_step_id")}
        template_by_id = {t["id"]: t for t in all_templates}

        for step_info in sorted(all_steps, key=lambda s: s.get("position", 0)):
            position = step_info["position"]
            step_id = step_info["id"]
            touch = touch_by_step.get(step_id)
            if not touch:
                raise RuntimeError(f"No touch found for step {position} (id={step_id})")
            tpl_id = touch.get("emailer_template_id")
            if not tpl_id or tpl_id not in template_by_id:
                raise RuntimeError(f"No template found for step {position} via touch {touch['id']}")

            merge_tags = MERGE_TAG_TEMPLATES[position]
            client.update_template(
                template_id=tpl_id,
                subject=merge_tags["subject"],
                body_html=merge_tags["body_html"],
            )
            # Update local step record
            step_local = next(s for s in steps if s["position"] == position)
            step_local["template_id"] = tpl_id
            step_local["merge_tag_subject"] = merge_tags["subject"]
            step_local["merge_tag_body"] = merge_tags["body_html"]
            log.info("Step %d → Template %s set to merge tags: %s / %s",
                     position, tpl_id, merge_tags["subject"], merge_tags["body_html"])
    except Exception as exc:
        log.error("Failed to set templates: %s", exc)
        return {
            "status": "error",
            "reason": f"template_setup_failed: {exc}",
            "sequence_id": sequence_id,
            "steps": steps,
        }

    return {
        "status": "created",
        "sequence_id": sequence_id,
        "sequence_name": sequence_name,
        "steps": steps,
        "cadence": cadence,
    }


def enroll_batch(
    sequence_id: str,
    contact_ids: list[str],
    mailbox_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Enrolluje kontakty do sekwencji z round-robin mailbox distribution.

    Args:
        sequence_id: ID sekwencji Apollo
        contact_ids: lista Apollo contact IDs do enrollment
        mailbox_ids: lista ID mailboxów (round-robin). Jeśli None, pobiera z Apollo.

    Returns:
        dict z:
        - enrolled: int
        - skipped: int
        - results: list[dict] per enrollment call
    """
    client = _get_apollo_client()

    # Pobierz mailboxy jeśli nie podane
    if not mailbox_ids:
        accounts = client.get_email_accounts()
        mailbox_ids = [acc["id"] for acc in accounts]
        log.info("Fetched %d active mailboxes", len(mailbox_ids))

    if not mailbox_ids:
        return {"status": "error", "reason": "no_mailboxes_available"}

    # Round-robin: podziel kontakty na grupy per mailbox
    groups: dict[str, list[str]] = {}
    for i, contact_id in enumerate(contact_ids):
        mailbox = mailbox_ids[i % len(mailbox_ids)]
        groups.setdefault(mailbox, []).append(contact_id)

    results = []
    total_enrolled = 0
    total_skipped = 0

    for mailbox_id, group_contact_ids in groups.items():
        try:
            response = client.add_to_sequence(
                sequence_id=sequence_id,
                contact_ids=group_contact_ids,
                email_account_id=mailbox_id,
            )

            skipped = response.get("skipped_contact_ids", {})
            enrolled_count = len(group_contact_ids) - len(skipped)
            total_enrolled += enrolled_count
            total_skipped += len(skipped)

            results.append({
                "mailbox_id": mailbox_id,
                "attempted": len(group_contact_ids),
                "enrolled": enrolled_count,
                "skipped": len(skipped),
                "skipped_details": skipped,
            })

            log.info("Enrolled %d/%d contacts via mailbox %s",
                     enrolled_count, len(group_contact_ids), mailbox_id)
        except Exception as exc:
            log.error("Enrollment failed for mailbox %s: %s", mailbox_id, exc)
            results.append({
                "mailbox_id": mailbox_id,
                "attempted": len(group_contact_ids),
                "enrolled": 0,
                "error": str(exc),
            })

        time.sleep(0.5)

    return {
        "enrolled": total_enrolled,
        "skipped": total_skipped,
        "total_attempted": len(contact_ids),
        "mailbox_count": len(mailbox_ids),
        "results": results,
    }


def activate_sequence(sequence_id: str) -> dict[str, Any]:
    """
    Aktywuje sekwencję (approve campaign + approve touches).

    Returns:
        dict z wynikiem aktywacji
    """
    client = _get_apollo_client()
    try:
        result = client.activate_sequence(sequence_id)
        log.info("Sequence %s activated: %s", sequence_id, result)
        return {"status": "activated", **result}
    except Exception as exc:
        log.error("Activation failed for %s: %s", sequence_id, exc)
        return {"status": "error", "reason": str(exc)}


def run_weekly_sequence(
    contacts_with_packs: list[dict],
    sequence_name: str | None = None,
    campaign_type: str = "Standard",
    market: str = "PL",
    cadence: list[int] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Pełny flow tygodniowej sekwencji — od sync pól do aktywacji.

    Args:
        contacts_with_packs: lista dict-ów z email + outreach_pack
        sequence_name: nazwa sekwencji (jeśli None, generowana automatycznie)
        campaign_type: typ kampanii (do generowania nazwy)
        market: rynek (PL/EN)
        cadence: override cadence [min, min, min]
        dry_run: jeśli True, nie wykonuje operacji Apollo (tylko walidacja)

    Returns:
        dict z pełnym raportem:
        - sequence: dane sekwencji
        - sync: wyniki sync custom fields
        - preflight: wyniki walidacji
        - enrollment: wyniki enrollment
        - activation: wynik aktywacji
        - summary: podsumowanie
    """
    from core.enrollment_preflight import preflight_batch

    report: dict[str, Any] = {
        "started_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "contacts_input": len(contacts_with_packs),
    }

    # Generuj nazwę sekwencji
    if sequence_name is None:
        sequence_name = generate_sequence_name(
            campaign_type=campaign_type,
            market=market,
        )
    report["sequence_name"] = sequence_name

    # ── STEP 1: Sync custom fields na kontaktach ──
    log.info("=== Step 1: Sync custom fields (%d contacts) ===", len(contacts_with_packs))
    if dry_run:
        sync_result = {"synced": 0, "failed": 0, "results": [], "contact_map": {},
                       "dry_run": True}
    else:
        sync_result = sync_batch_custom_fields(contacts_with_packs)
    report["sync"] = sync_result

    # ── STEP 2: Preflight check ──
    log.info("=== Step 2: Preflight check ===")
    preflight_contacts = []
    for item in contacts_with_packs:
        email = item["email"]
        from core.apollo_campaign_sync import outreach_pack_to_custom_fields
        cf_values = outreach_pack_to_custom_fields(item["outreach_pack"])
        cm = sync_result.get("contact_map", {}).get(email, {})
        preflight_contacts.append({
            "email": email,
            "custom_field_values": cf_values,
            "apollo_contact": cm.get("apollo_contact"),
        })
    preflight_result = preflight_batch(preflight_contacts)
    report["preflight"] = preflight_result

    enrollable_emails = preflight_result["enrollable_emails"]
    if not enrollable_emails:
        log.warning("No contacts passed preflight — aborting")
        report["enrollment"] = {"status": "skipped", "reason": "no_contacts_passed_preflight"}
        report["activation"] = {"status": "skipped"}
        report["summary"] = _build_summary(report)
        return report

    # ── STEP 3: Create weekly sequence ──
    log.info("=== Step 3: Create sequence '%s' ===", sequence_name)
    if dry_run:
        seq_result = {"status": "dry_run", "sequence_name": sequence_name}
    else:
        seq_result = create_weekly_sequence(
            sequence_name=sequence_name,
            cadence=cadence,
        )
    report["sequence"] = seq_result

    if seq_result.get("status") not in ("created", "dry_run"):
        log.error("Sequence creation failed — aborting")
        report["enrollment"] = {"status": "skipped", "reason": "sequence_creation_failed"}
        report["activation"] = {"status": "skipped"}
        report["summary"] = _build_summary(report)
        return report

    sequence_id = seq_result.get("sequence_id")

    # ── STEP 4: Enroll ──
    log.info("=== Step 4: Enroll %d contacts ===", len(enrollable_emails))
    contact_ids = [
        sync_result["contact_map"][email]["contact_id"]
        for email in enrollable_emails
        if email in sync_result.get("contact_map", {})
    ]

    if dry_run:
        enrollment_result = {"status": "dry_run", "would_enroll": len(contact_ids)}
    else:
        enrollment_result = enroll_batch(
            sequence_id=sequence_id,
            contact_ids=contact_ids,
        )
    report["enrollment"] = enrollment_result

    # ── STEP 5: Activate ──
    log.info("=== Step 5: Activate sequence ===")
    if dry_run:
        activation_result = {"status": "dry_run"}
    else:
        activation_result = activate_sequence(sequence_id)
    report["activation"] = activation_result

    report["finished_at"] = datetime.now().isoformat()
    report["summary"] = _build_summary(report)

    log.info("=== Weekly sequence complete: %s ===", report["summary"].get("verdict"))
    return report


def _build_summary(report: dict) -> dict:
    """Buduje podsumowanie z raportu."""
    sync = report.get("sync", {})
    preflight = report.get("preflight", {})
    enrollment = report.get("enrollment", {})
    activation = report.get("activation", {})

    enrolled = enrollment.get("enrolled", 0)
    skipped = enrollment.get("skipped", 0)
    preflight_passed = preflight.get("passed", 0)
    preflight_failed = preflight.get("failed", 0)

    if report.get("dry_run"):
        verdict = "DRY_RUN_OK"
    elif activation.get("status") == "activated" and enrolled > 0:
        verdict = "SUCCESS"
    elif enrolled > 0:
        verdict = "PARTIAL_SUCCESS"
    else:
        verdict = "FAILED"

    return {
        "verdict": verdict,
        "contacts_input": report.get("contacts_input", 0),
        "contacts_synced": sync.get("synced", 0),
        "preflight_passed": preflight_passed,
        "preflight_failed": preflight_failed,
        "enrolled": enrolled,
        "enrollment_skipped": skipped,
        "sequence_name": report.get("sequence_name", ""),
        "sequence_id": report.get("sequence", {}).get("sequence_id"),
        "activated": activation.get("status") == "activated",
    }
