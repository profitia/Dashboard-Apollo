"""
News Message Generator — generuje 3-krokową sekwencję mailową per kontakt (3 tiery).

Używa LLM (OpenAI) + fallback heurystyczny.
Wejście: ArticleContent + ContactRecord + tier context
Wyjście: OutreachPack (email_1 / follow_up_1 / follow_up_2)
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

SIGNATURE_PLAIN = """
Z poważaniem,
Tomasz Uściński
Head of Sales | Profitia
tomasz.uscinski@profitia.pl | +48 787 417 293"""

TIER_PERSPECTIVES = {
    "tier_1_c_level": """
Perspektywa TIER 1 — C-Level / Zarząd:
- Mów językiem: marża, EBIT, odporność kosztowa, kontrola nad wynikiem, przewaga negocjacyjna
- Pain points: presja na wynik, nieuzasadnione podwyżki dostawców bez możliwości obrony, brak wglądu w realne możliwości oszczędności
- Value prop: powtarzalny standard decyzji zakupowych, lepsza kontrola nad wynikiem bez mikromanagementu zakupów
- Proof point: firmy z przygotowaniem negocjacyjnym blokują 30-50% proponowanych podwyżek dostawców
- CTA: lekkie, strategiczne — "spojrzenie na jedną kategorię kosztową" lub "15-min rozmowa o podejściu"
- Unikaj: szczegółów operacyjnych, listy modułów, "narzędzie zakupowe"
""",
    "tier_2_procurement_management": """
Perspektywa TIER 2 — Procurement Management / Liderzy zakupów:
- Mów językiem: savings delivery, standaryzacja przygotowania negocjacji, jakość pracy zespołu, redukcja nieuzasadnionych podwyżek
- Pain points: brak powtarzalnego standardu przygotowania negocjacji, trudność w uzasadnieniu decyzji zakupowych zarządowi, presja na wyniki
- Value prop: systematyczne przygotowanie każdej negocjacji (benchmark, cost drivers, analiza dostawcy, plan rozmowy) — nie jednorazowy projekt
- Proof point: 5 pytań przed każdą negocjacją, które systematycznie poprawiają wyniki o 10-20%
- CTA: praktyczne — "sprawdzenie podejścia na jednej kategorii" lub "krótka rozmowa o standardzie przygotowania"
- Unikaj: zbyt strategicznego języka zarządu, szczegółów technicznych
""",
    "tier_3_buyers_operational": """
Perspektywa TIER 3 — Buyers / Category Managers / Operacyjni:
- Mów językiem: praktyczne przygotowanie do rozmowy, argumentacja wobec dostawcy, ocena zasadności oferty/podwyżki, benchmark, cost drivers
- Pain points: brak pewności przed trudną negocjacją, zbyt mało danych do obrony ceny, improwizacja zamiast struktury
- Value prop: konkretna pomoc przy jednej negocjacji — benchmark dostawcy, cost drivers, gotowy plan rozmowy
- Proof point: kupcy z SpendGuru wchodzą na negocjacje ze strukturą zamiast improwizacją
- CTA: bardzo konkretne — "czy masz teraz trudną negocjację?" lub "pokażę na jednym dostawcy"
- Unikaj: języka strategicznego, ogólnych obietnic, zbyt formalnego tonu
""",
    "tier_uncertain": """
Perspektywa OGÓLNA (Tier nieustalony):
- Neutralny ton, skoncentrowany na problemie biznesowym
- Używaj języka procurement/zakupów bez zbędnego uszczegóławiania
- CTA: miękkie, bez presji
""",
}


@dataclass
class OutreachPack:
    email_1: dict   # {subject, body, body_html}
    follow_up_1: dict
    follow_up_2: dict
    review_notes: dict
    tier: str
    tier_label: str
    contact_email: str
    contact_name: str
    generated_by: str  # llm | heuristic


def _load_prompt_template(campaign_dir: str) -> str:
    """Ładuje szablon promptu z katalogu kampanii."""
    prompt_path = os.path.join(campaign_dir, "prompts", "message_writer.md")
    try:
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Prompt template not found at %s — using minimal inline prompt", prompt_path)
        return _minimal_prompt()


def _minimal_prompt() -> str:
    return """Wygeneruj 3-krokową sekwencję mailową po polsku dla kontaktu B2B.
Artykuł: {{article_title}} ({{article_source}})
Kontakt: {{vocative_first_name}} {{last_name}}, {{job_title}} @ {{company_name}}
Tier: {{tier_label}}
Lead artykułu: {{article_lead}}

Odpowiedz WYŁĄCZNIE w JSON: {"email_1": {"subject": "...", "body": "..."}, "follow_up_1": {"subject": "...", "body": "..."}, "follow_up_2": {"subject": "...", "body": "..."}, "review_notes": {"trigger_used": "...", "hypothesis": "...", "cta_rationale": "...", "tier_alignment": "..."}}"""


def _fill_prompt(
    template: str,
    contact,
    article,
    article_key_facts: str,
) -> str:
    """Wypełnia zmienne w szablonie promptu."""
    from datetime import datetime

    tier = contact.tier
    tier_label = contact.tier_label
    perspective = TIER_PERSPECTIVES.get(tier, TIER_PERSPECTIVES["tier_uncertain"])

    # Gender form
    gender_form_map = {
        "male": "Pan (forma: Panu/Pana/Pan)",
        "female": "Pani (forma: Pani)",
    }
    gender_form = gender_form_map.get(getattr(contact, "_gender", ""), "neutralnie: Pani/Pana")

    # Article date
    pub_date = article.published_at or ""
    if pub_date and "T" in pub_date:
        pub_date = pub_date[:10]

    body_excerpt = (article.body or "")[:1500]

    replacements = {
        "{{vocative_first_name}}": contact.first_name,
        "{{last_name}}": contact.last_name,
        "{{job_title}}": contact.job_title,
        "{{company_name}}": contact.company_name,
        "{{tier_label}}": tier_label,
        "{{article_title}}": article.title,
        "{{article_source}}": article.source_id,
        "{{article_date}}": pub_date,
        "{{article_url}}": article.canonical_url,
        "{{article_lead}}": article.lead or "",
        "{{article_body_excerpt}}": body_excerpt,
        "{{article_key_facts}}": article_key_facts,
        "{{tier_perspective}}": perspective.strip(),
        "{{gender_form}}": gender_form,
    }

    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result


def _body_to_html(body: str) -> str:
    """Konwertuje plain text do prostego HTML (bez podpisu HTML — dodawany przez Apollo)."""
    # Import istniejącego modułu jeśli dostępny
    try:
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from core.email_signature import body_to_html
        return body_to_html(body)
    except ImportError:
        pass

    # Fallback: prosta konwersja
    lines = body.strip().split("\n")
    html_parts = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            html_parts.append(f"<p>{stripped}</p>")
        else:
            html_parts.append("<br>")
    return "\n".join(html_parts)


def _generate_via_llm(
    prompt: str,
) -> dict | None:
    """Wywołuje LLM i parsuje odpowiedź."""
    try:
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from llm_client import generate_json, is_llm_available
        if not is_llm_available():
            return None
    except ImportError:
        return None

    result = generate_json(
        prompt=prompt,
        system_prompt=(
            "Jesteś ekspertem od komunikacji B2B i outreachu. "
            "Odpowiadasz WYŁĄCZNIE w JSON. Żadnych komentarzy, żadnego markdown poza JSON."
        ),
        temperature=0.6,
        max_tokens=3000,
    )
    return result


def _generate_fallback(contact, article, tier: str) -> dict:
    """Heurystyczny fallback gdy LLM niedostępny."""
    company = contact.company_name
    first = contact.first_name
    title_str = article.title or "(artykuł)"
    source = article.source_id or "serwisu branżowego"
    lead = article.lead or ""
    trigger_excerpt = lead[:200] if lead else title_str

    perspective_short = {
        "tier_1_c_level": "marży i odporności kosztowej firmy",
        "tier_2_procurement_management": "jakości przygotowania zespołu zakupowego",
        "tier_3_buyers_operational": "przygotowania do konkretnych negocjacji z dostawcami",
    }.get(tier, "efektywności zakupowej")

    cta_phone = "Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę śmiało przesłać numer - oddzwonię."

    body_1 = f"""Dzień dobry,

natknąłem się na artykuł w {source} dotyczący {trigger_excerpt[:150]}.

Zakładam, że z perspektywy {company} temat {perspective_short} jest istotny - szczególnie w kontekście negocjacji z dostawcami.

W Profitii pomagamy firmom z branży produkcyjnej i FMCG przygotowywać się do negocjacji zakupowych w sposób systematyczny - tak, by każda rozmowa z dostawcą była oparta na danych, a nie improwizacji.

Czy byłby Pan/Pani otwarty/a na krótką rozmowę - 15 minut - żeby sprawdzić, czy nasze podejście ma sens w kontekście {company}?

{cta_phone}
{SIGNATURE_PLAIN}"""

    body_2 = f"""Dzień dobry,

piszę ponownie w nawiązaniu do artykułu o {title_str[:80]}.

Jeden konkretny mechanizm, który może być istotny dla {company}: systematyczna weryfikacja zasadności proponowanych podwyżek od dostawców - zanim się na nie zgodzisz lub odrzucisz.

Wiele firm traci kilka punktów procentowych marży rocznie z powodu braku danych do obrony ceny. SpendGuru pomaga to zmienić - bez wielomiesięcznych projektów.

Czy byłoby warto porozmawiać 15 minut?

{cta_phone}
{SIGNATURE_PLAIN}"""

    body_3 = f"""Dzień dobry,

ostatnia wiadomość ode mnie.

Jeśli temat negocjacji zakupowych jest aktualny dla {company} - chętnie pokażę przykład przygotowania do jednej negocjacji. Bez zobowiązań.

{cta_phone}
{SIGNATURE_PLAIN}"""

    return {
        "email_1": {"subject": f"Artykuł o {company[:30]} - negocjacje zakupowe", "body": body_1},
        "follow_up_1": {"subject": f"Re: {company[:30]} - jeden konkretny mechanizm", "body": body_2},
        "follow_up_2": {"subject": f"Ostatnia wiadomość - {company[:30]}", "body": body_3},
        "review_notes": {
            "trigger_used": title_str,
            "hypothesis": f"Firma {company} może mieć wyzwania z {perspective_short}",
            "cta_rationale": "Miękkie CTA — krótka rozmowa bez zobowiązań",
            "tier_alignment": "Fallback — heurystyczny, bez głębokiej personalizacji",
        },
    }


def generate_outreach_pack(
    contact,
    article,
    campaign_dir: str,
    article_key_facts: str = "",
) -> OutreachPack:
    """
    Generuje OutreachPack dla jednego kontaktu.

    Args:
        contact: ContactRecord
        article: ArticleContent
        campaign_dir: ścieżka do katalogu kampanii (dla promptów)
        article_key_facts: dodatkowe fakty z artykułu do promptu

    Returns:
        OutreachPack
    """
    tier = contact.tier
    tier_label = contact.tier_label

    # Load & fill prompt
    template = _load_prompt_template(campaign_dir)
    filled_prompt = _fill_prompt(template, contact, article, article_key_facts)

    # Try LLM
    result = _generate_via_llm(filled_prompt)
    generated_by = "llm"

    if not result or "email_1" not in result:
        log.info("LLM unavailable or failed — using heuristic fallback for %s", contact.email)
        result = _generate_fallback(contact, article, tier)
        generated_by = "heuristic"

    # Build OutreachPack
    def _enrich_step(step: dict) -> dict:
        body = step.get("body", "")
        # Append signature if not present
        if SIGNATURE_PLAIN.strip() not in body:
            body = body.rstrip() + "\n" + SIGNATURE_PLAIN
        return {
            "subject": step.get("subject", ""),
            "body": body,
            "body_html": _body_to_html(body),
            "body_core": step.get("body", ""),  # without signature — for Apollo custom fields
        }

    return OutreachPack(
        email_1=_enrich_step(result.get("email_1", {})),
        follow_up_1=_enrich_step(result.get("follow_up_1", {})),
        follow_up_2=_enrich_step(result.get("follow_up_2", {})),
        review_notes=result.get("review_notes", {}),
        tier=tier,
        tier_label=tier_label,
        contact_email=contact.email,
        contact_name=contact.full_name,
        generated_by=generated_by,
    )
