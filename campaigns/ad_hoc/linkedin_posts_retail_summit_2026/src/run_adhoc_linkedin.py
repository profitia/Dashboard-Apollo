#!/usr/bin/env python3
"""
AdHoc Campaign Builder — LinkedIn Posts Pipeline.

Flow: posts_analysis.json → ICP filter → Apollo enrichment → LLM emails → CSV/JSON output.
Entirely separate from standard campaign and CSV import flows.

Usage:
    python campaigns/ad_hoc/linkedin_posts_retail_summit_2026/src/run_adhoc_linkedin.py --config campaigns/ad_hoc/linkedin_posts_retail_summit_2026/configs/retail_summit_2026.yaml --mode draft
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ADHOC_ROOT = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_ADHOC_ROOT)))

# Add project src/ and Integracje/ to path for reusing existing modules
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src"))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "Integracje"))

import yaml

# ── Imports from existing codebase ─────────────────────────────
try:
    from llm_client import generate_json, is_llm_available
except ImportError:
    print("[WARN] llm_client not available — email generation will fail.")
    def generate_json(*a, **kw): return None
    def is_llm_available(): return False

try:
    from core.polish_names import resolve_polish_contact, get_vocative, get_gender
except ImportError:
    print("[WARN] polish_names not available — gender/vocative defaults to unknown.")
    def resolve_polish_contact(first_name, **kw): return {"gender": "unknown", "vocative": first_name, "greeting": f"Dzień dobry,"}
    def get_vocative(name): return name
    def get_gender(name): return "unknown"

try:
    from core.email_signature import SIGNATURE_PLAIN
except ImportError:
    SIGNATURE_PLAIN = "\nPozdrawiam serdecznie,\nTomasz Uściński"

try:
    from apollo_client import ApolloClient
except ImportError:
    ApolloClient = None
    print("[WARN] apollo_client not available — enrichment will be skipped.")


# ── ICP title matching ─────────────────────────────────────────

ICP_TITLE_KEYWORDS = [
    "ceo", "chief executive", "prezes", "president",
    "cfo", "chief financial", "dyrektor finansowy", "finance director", "vp finance",
    "coo", "chief operating", "dyrektor operacyjny", "operations director",
    "cpo", "chief procurement", "dyrektor zakupów", "procurement director",
    "chief supply chain", "supply chain director", "dyrektor łańcucha dostaw",
    "managing director", "dyrektor zarządzający", "general manager",
    "board member", "członek zarządu", "member of the board",
    "category director", "category manager", "senior category",
    "controlling director", "head of controlling",
    "owner", "właściciel", "founder", "założyciel",
    "vp", "vice president", "wiceprezes",
    "country manager", "country director",
    "head of procurement", "head of purchasing", "head of supply chain",
    "head of finance", "head of operations",
    "commercial director", "dyrektor handlowy",
    "business unit director",
]


def matches_icp_title(title: str) -> bool:
    """Check if Apollo title matches ICP roles."""
    if not title:
        return False
    t = title.lower()
    return any(kw in t for kw in ICP_TITLE_KEYWORDS)


# ── Load config ────────────────────────────────────────────────

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Load context files ─────────────────────────────────────────

def load_context_files() -> dict:
    """Load context/*.md files from project root."""
    ctx_dir = os.path.join(_PROJECT_ROOT, "context")
    files = {}
    if not os.path.isdir(ctx_dir):
        return files
    for fname in sorted(os.listdir(ctx_dir)):
        if fname.endswith(".md"):
            fpath = os.path.join(ctx_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                files[fname] = f.read()
    return files


# ── Load posts analysis ───────────────────────────────────────

def load_posts_analysis(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Extract candidates ────────────────────────────────────────

def extract_candidates(posts: list) -> tuple[list, list]:
    """Extract candidate contacts and rejected contacts from posts analysis."""
    candidates = []
    rejected = []

    for post in posts:
        for p in post.get("participants", []):
            record = {
                "name": p["name"],
                "company": p.get("company"),
                "role_in_panel": p.get("role_in_panel", ""),
                "known_title": p.get("known_title", ""),
                "credentials": p.get("credentials", ""),
                "post_id": post["post_id"],
                "post_url": post["post_url"],
                "panel_title": post["panel_title"],
                "event": post.get("event", "Poland & CEE Retail Summit 2026"),
                "key_themes": post.get("key_themes", []),
                "business_problems": post.get("business_problems", []),
                "negotiation_intelligence_angle": post.get("negotiation_intelligence_angle", ""),
                "industry_fit": p.get("industry_fit", ""),
                "personalization_angle": p.get("personalization_angle", ""),
            }

            if p.get("icp_status") == "candidate":
                candidates.append(record)
            else:
                record["rejection_reason"] = p.get("rejection_reason", "unknown")
                rejected.append(record)

    return candidates, rejected


# ── Apollo enrichment ──────────────────────────────────────────

def enrich_contact_apollo(client, name: str, company: str | None) -> dict | None:
    """
    Try to find and enrich a contact via Apollo.
    Strategy: search by name + company domain, then enrich best match.
    """
    if client is None:
        return None

    parts = name.strip().split()
    if len(parts) < 2:
        return None
    first_name = parts[0]
    last_name = " ".join(parts[1:])

    # Try people/match enrichment with name + company
    try:
        person = client.enrich_person(
            first_name=first_name,
            last_name=last_name,
            organization_name=company,
        )
        if person:
            return person
    except Exception as e:
        print(f"  [Apollo] enrich_person error for {name} @ {company}: {e}")

    # Fallback: search_people
    try:
        q = f"{first_name} {last_name}"
        people, total = client.search_people(
            q_keywords=q,
            per_page=5,
        )
        if people:
            # Find best match by company name
            if company:
                company_lower = company.lower()
                for p in people:
                    org = (p.get("organization", {}) or {}).get("name", "").lower()
                    if company_lower in org or org in company_lower:
                        return p
            # If no company match, return first result
            return people[0]
    except Exception as e:
        print(f"  [Apollo] search_people error for {name}: {e}")

    return None


def extract_apollo_data(person: dict) -> dict:
    """Extract relevant fields from Apollo person response."""
    if not person:
        return {}

    email = person.get("email") or ""
    email_status = person.get("email_status", "")
    linkedin = person.get("linkedin_url") or ""
    title = person.get("title") or ""
    city = person.get("city") or ""
    country = person.get("country") or ""
    org = person.get("organization") or {}
    company_name = org.get("name") or person.get("organization_name") or ""

    # Determine data confidence
    confidence = "high"
    if email_status not in ("verified", "valid"):
        confidence = "medium" if email else "low"
    if not email:
        confidence = "no_email"

    return {
        "apollo_email": email,
        "apollo_email_status": email_status,
        "apollo_linkedin_url": linkedin,
        "apollo_title": title,
        "apollo_company": company_name,
        "apollo_city": city,
        "apollo_country": country,
        "data_confidence": confidence,
        "apollo_id": person.get("id", ""),
    }


# ── Polish name resolution ────────────────────────────────────

def resolve_contact_polish(name: str) -> dict:
    """Resolve gender, vocative, and greeting for a Polish contact."""
    parts = name.strip().split()
    first_name = parts[0] if parts else name

    info = resolve_polish_contact(first_name)
    gender = info.get("gender", "unknown")

    if gender == "female":
        greeting_formal = "Pani"
    elif gender == "male":
        greeting_formal = "Panie"
    else:
        greeting_formal = ""

    vocative = info.get("vocative", first_name)
    if greeting_formal:
        greeting = f"Dzień dobry {greeting_formal} {vocative},"
    else:
        greeting = f"Dzień dobry,"

    return {
        "first_name": first_name,
        "recipient_gender": gender,
        "first_name_vocative": vocative,
        "greeting_formal": greeting_formal,
        "greeting": greeting,
    }


# ── Generate emails via LLM ───────────────────────────────────

def generate_email_sequence(
    contact: dict,
    polish: dict,
    context_files: dict,
) -> dict | None:
    """Generate 3-email sequence via LLM."""
    prompt_path = os.path.join(_ADHOC_ROOT, "prompts", "adhoc_email_writer.md")

    payload = {
        "contact_name": contact["name"],
        "contact_title": contact.get("apollo_title") or contact.get("known_title", ""),
        "company": contact.get("apollo_company") or contact.get("company", ""),
        "recipient_gender": polish["recipient_gender"],
        "first_name_vocative": polish["first_name_vocative"],
        "greeting_formal": polish["greeting_formal"],
        "panel_title": contact["panel_title"],
        "post_url": contact["post_url"],
        "event_name": contact.get("event", "Poland & CEE Retail Summit 2026"),
        "key_themes": contact.get("key_themes", []),
        "business_problems": contact.get("business_problems", []),
        "personalization_angle": contact.get("personalization_angle", ""),
        "hypothesis": contact.get("negotiation_intelligence_angle", ""),
        "suggested_framework": "Cost/Trend/Dostawca/Decyzja",
        "industry_fit": contact.get("industry_fit", ""),
    }

    result = generate_json(
        agent_name="AdHocEmailWriter",
        prompt_path=prompt_path,
        user_payload=payload,
        context_files=context_files,
        relevant_context_keys=["00_master", "01_offer", "03_messaging", "05_quality"],
        max_tokens=3000,
        temperature=0.5,
    )

    return result


# ── Build personalization memo ─────────────────────────────────

def build_personalization_memo(contact: dict, polish: dict) -> dict:
    return {
        "panel_title": contact["panel_title"],
        "source_post_url": contact["post_url"],
        "why_selected": contact.get("personalization_angle", ""),
        "panel_reference": f"Panelista w panelu \"{contact['panel_title']}\" na {contact.get('event', 'Poland & CEE Retail Summit 2026')}",
        "hypothesis_from_panel": contact.get("negotiation_intelligence_angle", ""),
        "business_pain": "; ".join(contact.get("business_problems", [])),
        "suggested_angle": contact.get("personalization_angle", ""),
        "suggested_framework_application": "Cost transparency → Trend/Forecast → Dostawca/Ryzyko → Decyzja/Negocjacja",
        "suggested_cta": "15–20 min rozmowy o przygotowaniu do negocjacji z dostawcami",
        "industry_fit": contact.get("industry_fit", ""),
        "recipient_gender": polish["recipient_gender"],
        "first_name_vocative": polish["first_name_vocative"],
    }


# ── Determine final status ────────────────────────────────────

def determine_status(contact: dict, apollo: dict, emails: dict | None) -> str:
    if not apollo.get("apollo_email"):
        return "no_valid_contact"
    if apollo.get("data_confidence") == "low" and not matches_icp_title(apollo.get("apollo_title", "")):
        return "rejected_not_icp"
    if not emails:
        return "insufficient_personalization"
    return "ready_for_review"


# ── Output writers ─────────────────────────────────────────────

def write_json_output(records: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  [Output] JSON → {path}")


def write_csv_output(records: list, path: str):
    if not records:
        return

    fieldnames = [
        "post_url", "panel_title", "contact_name", "contact_title", "company",
        "industry_fit", "icp_fit_reason", "apollo_email", "apollo_linkedin_url",
        "data_confidence", "personalization_memo", "email_1_subject", "email_1_body",
        "email_2_subject", "email_2_body", "email_3_subject", "email_3_body", "status",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            row = {
                "post_url": r.get("post_url", ""),
                "panel_title": r.get("panel_title", ""),
                "contact_name": r.get("name", ""),
                "contact_title": r.get("apollo_title", r.get("known_title", "")),
                "company": r.get("apollo_company", r.get("company", "")),
                "industry_fit": r.get("industry_fit", ""),
                "icp_fit_reason": r.get("personalization_angle", ""),
                "apollo_email": r.get("apollo_email", ""),
                "apollo_linkedin_url": r.get("apollo_linkedin_url", ""),
                "data_confidence": r.get("data_confidence", ""),
                "personalization_memo": json.dumps(r.get("personalization_memo", {}), ensure_ascii=False),
                "email_1_subject": r.get("email_1_subject", ""),
                "email_1_body": r.get("email_1_body", ""),
                "email_2_subject": r.get("email_2_subject", ""),
                "email_2_body": r.get("email_2_body", ""),
                "email_3_subject": r.get("email_3_subject", ""),
                "email_3_body": r.get("email_3_body", ""),
                "status": r.get("status", ""),
            }
            writer.writerow(row)
    print(f"  [Output] CSV → {path}")


def write_rejected_csv(rejected: list, path: str):
    if not rejected:
        return

    fieldnames = ["name", "company", "role_in_panel", "panel_title", "post_url", "rejection_reason"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rejected:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"  [Output] Rejected CSV → {path}")


# ── Run report ─────────────────────────────────────────────────

def generate_report(results: list, rejected: list, output_dir: str, config: dict):
    """Generate a human-readable run report."""
    ready = [r for r in results if r["status"] == "ready_for_review"]
    no_contact = [r for r in results if r["status"] == "no_valid_contact"]
    no_icp = [r for r in results if r["status"] == "rejected_not_icp"]
    insufficient = [r for r in results if r["status"] == "insufficient_personalization"]

    lines = [
        f"# AdHoc Campaign Report — {config.get('campaign_name', 'adhoc')}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {config.get('mode', 'draft')}",
        "",
        "## Summary",
        f"- Candidates processed: {len(results)}",
        f"- **Ready for review: {len(ready)}**",
        f"- No valid contact (Apollo): {len(no_contact)}",
        f"- Rejected (not ICP title): {len(no_icp)}",
        f"- Insufficient personalization: {len(insufficient)}",
        f"- Pre-rejected (analysis phase): {len(rejected)}",
        "",
        "## Ready for Review",
    ]

    for r in ready:
        lines.append(f"### {r['name']} — {r.get('apollo_company', r.get('company', ''))}")
        lines.append(f"- Title: {r.get('apollo_title', 'n/a')}")
        lines.append(f"- Email: {r.get('apollo_email', 'n/a')}")
        lines.append(f"- Panel: {r['panel_title']}")
        lines.append(f"- Angle: {r.get('personalization_angle', 'n/a')}")
        lines.append(f"- Data confidence: {r.get('data_confidence', 'n/a')}")
        if r.get("email_1_subject"):
            lines.append(f"- Email 1 subject: {r['email_1_subject']}")
        lines.append("")

    if no_contact:
        lines.append("## No Valid Contact (skipped)")
        for r in no_contact:
            lines.append(f"- {r['name']} ({r.get('company', '')}) — no email found in Apollo")
        lines.append("")

    if rejected:
        lines.append("## Pre-rejected Contacts")
        for r in rejected:
            lines.append(f"- {r['name']} ({r.get('company', '')}) — {r.get('rejection_reason', '')}")
        lines.append("")

    report_path = os.path.join(output_dir, "run_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [Output] Report → {report_path}")
    return report_path


# ── Main pipeline ──────────────────────────────────────────────

def run_pipeline(config: dict):
    print("\n" + "=" * 60)
    print("  AdHoc Campaign Builder — LinkedIn Posts")
    print("=" * 60)

    mode = config.get("mode", "draft")
    campaign_name = config.get("campaign_name", "adhoc_linkedin")

    # Resolve posts analysis path
    posts_path = os.path.join(_PROJECT_ROOT, config["source"]["posts_analysis"])
    if not os.path.exists(posts_path):
        print(f"[ERROR] Posts analysis file not found: {posts_path}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(_ADHOC_ROOT, "output", f"{timestamp}_{campaign_name}")
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    print("\n[1/7] Loading posts analysis...")
    posts = load_posts_analysis(posts_path)
    print(f"  Loaded {len(posts)} posts")

    # Extract candidates
    print("\n[2/7] Extracting and filtering candidates by ICP...")
    candidates, rejected = extract_candidates(posts)
    print(f"  Candidates: {len(candidates)}")
    print(f"  Pre-rejected: {len(rejected)}")

    # Load context files for LLM
    context_files = load_context_files()
    print(f"  Context files loaded: {len(context_files)}")

    # Initialize Apollo
    apollo_client = None
    if config.get("apollo", {}).get("enrich_contacts", True) and ApolloClient is not None:
        try:
            apollo_client = ApolloClient()
            print("\n[3/7] Apollo client initialized")
        except Exception as e:
            print(f"\n[3/7] Apollo client FAILED: {e}")
            print("  Continuing without Apollo enrichment...")
    else:
        print("\n[3/7] Apollo enrichment skipped (config or module not available)")

    # Check LLM
    llm_ok = is_llm_available()
    if llm_ok:
        print("  LLM available ✓")
    else:
        print("  [WARN] LLM not available — email generation will produce empty results")

    # Process candidates
    print("\n[4/7] Processing candidates (Apollo + Polish names)...")
    results = []
    for i, cand in enumerate(candidates, 1):
        name = cand["name"]
        company = cand.get("company") or ""
        print(f"\n  [{i}/{len(candidates)}] {name} ({company})")

        # Polish name resolution
        polish = resolve_contact_polish(name)
        print(f"    Gender: {polish['recipient_gender']}, Vocative: {polish['first_name_vocative']}")

        # Apollo enrichment
        apollo_data = {}
        if apollo_client:
            print(f"    Querying Apollo...")
            person = enrich_contact_apollo(apollo_client, name, company)
            apollo_data = extract_apollo_data(person)
            if apollo_data.get("apollo_email"):
                print(f"    ✓ Email: {apollo_data['apollo_email']} ({apollo_data['data_confidence']})")
                print(f"    Title: {apollo_data.get('apollo_title', 'n/a')}")
            else:
                print(f"    ✗ No email found")
            # Respect rate limits
            time.sleep(1)
        else:
            apollo_data = {"data_confidence": "not_enriched", "apollo_email": "", "apollo_title": ""}
            print(f"    Apollo skipped (no client)")

        # Merge data
        record = {**cand, **apollo_data, **polish}
        record["personalization_memo"] = build_personalization_memo(cand, polish)
        results.append(record)

    # Filter: skip email generation for no-email contacts
    print(f"\n[5/7] Generating email sequences via LLM...")
    for i, record in enumerate(results, 1):
        name = record["name"]

        # Skip if no email and config says so
        if config.get("quality", {}).get("skip_no_email", True) and not record.get("apollo_email"):
            record["status"] = "no_valid_contact"
            print(f"  [{i}/{len(results)}] {name} — SKIPPED (no email)")
            continue

        # Skip if title doesn't match ICP (only if we have Apollo title)
        apollo_title = record.get("apollo_title", "")
        if apollo_title and not matches_icp_title(apollo_title):
            if config.get("quality", {}).get("skip_no_icp_title", True):
                record["status"] = "rejected_not_icp"
                print(f"  [{i}/{len(results)}] {name} — SKIPPED (title '{apollo_title}' not ICP)")
                continue

        print(f"  [{i}/{len(results)}] {name} — generating emails...")
        emails = generate_email_sequence(record, record, context_files)

        if emails:
            record["email_1_subject"] = emails.get("email_1_subject", "")
            record["email_1_body"] = emails.get("email_1_body", "")
            record["email_2_subject"] = emails.get("email_2_subject", "")
            record["email_2_body"] = emails.get("email_2_body", "")
            record["email_3_subject"] = emails.get("email_3_subject", "")
            record["email_3_body"] = emails.get("email_3_body", "")
            record["_llm_model_used"] = emails.get("_llm_model_used", "")
            record["status"] = "ready_for_review"
            print(f"    ✓ Emails generated (model: {record['_llm_model_used']})")
        else:
            record["status"] = "insufficient_personalization"
            print(f"    ✗ LLM failed — insufficient_personalization")

    # Write outputs
    print(f"\n[6/7] Writing outputs to {output_dir}/...")

    # Full results JSON
    write_json_output(results, os.path.join(output_dir, "campaign_results.json"))

    # CSV for review
    write_csv_output(results, os.path.join(output_dir, "campaign_results.csv"))

    # Rejected contacts
    write_rejected_csv(rejected, os.path.join(output_dir, "rejected_contacts.csv"))

    # Per-contact JSONs (for detailed review)
    contacts_dir = os.path.join(output_dir, "contacts")
    os.makedirs(contacts_dir, exist_ok=True)
    for r in results:
        safe_name = r["name"].replace(" ", "_").lower()
        contact_path = os.path.join(contacts_dir, f"{safe_name}.json")
        write_json_output(r, contact_path)

    # Generate report
    print(f"\n[7/7] Generating report...")
    report_path = generate_report(results, rejected, output_dir, config)

    # Print summary
    ready = [r for r in results if r["status"] == "ready_for_review"]
    no_contact = [r for r in results if r["status"] == "no_valid_contact"]
    not_icp = [r for r in results if r["status"] == "rejected_not_icp"]
    insuff = [r for r in results if r["status"] == "insufficient_personalization"]

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total candidates:          {len(results)}")
    print(f"  ✓ Ready for review:        {len(ready)}")
    print(f"  ✗ No valid contact:        {len(no_contact)}")
    print(f"  ✗ Rejected (not ICP):      {len(not_icp)}")
    print(f"  ✗ Insufficient:            {len(insuff)}")
    print(f"  Pre-rejected:              {len(rejected)}")
    print()

    if ready:
        print("  TOP 3 PERSONALIZATIONS:")
        for r in ready[:3]:
            print(f"  ─ {r['name']} ({r.get('apollo_company', r.get('company', ''))})")
            print(f"    Panel: {r['panel_title'][:60]}...")
            print(f"    Angle: {r.get('personalization_angle', '')[:80]}...")
            if r.get("email_1_subject"):
                print(f"    Subject 1: {r['email_1_subject']}")
            print()

    print(f"  Output dir: {output_dir}")
    print(f"  Report:     {report_path}")
    print("=" * 60 + "\n")


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AdHoc Campaign Builder — LinkedIn Posts")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--mode", default="draft", choices=["draft", "live"], help="Run mode")
    args = parser.parse_args()

    config_path = os.path.join(_PROJECT_ROOT, args.config)
    if not os.path.exists(config_path):
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    config["mode"] = args.mode

    run_pipeline(config)


if __name__ == "__main__":
    main()
