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

# Linki Calendly per tier (tier_calendly_link wstrzykiwany do promptu)
CALENDLY_URLS: dict[str, str] = {
    "tier_1_c_level": "https://calendly.com/profitia/zakupy-a-marza-firmy",
    "tier_2_procurement_management": "https://calendly.com/profitia/standard-negocjacji-i-oszczednosci",
    "tier_3_buyers_operational": "https://calendly.com/profitia/standard-negocjacji-i-oszczednosci",
    "tier_uncertain": "https://calendly.com/profitia/standard-negocjacji-i-oszczednosci",
}

# Limity słów per krok (walidacja po generacji)
WORD_COUNT_LIMITS: dict[str, tuple[int, int]] = {
    "email_1":     (120, 170),
    "follow_up_1": (60, 100),
    "follow_up_2": (40, 80),
}

TIER_PERSPECTIVES = {
    "tier_1_c_level": """
Perspektywa TIER 1 — C-Level / Zarząd:
- Narracja: marża, rentowność, EBIT, presja kosztowa, przewidywalność wyników, kontrola ryzyka
- Pain points: presja na wynik, nieuzasadnione podwyżki dostawców bez możliwości obrony, brak wglądu w realne oszczędności, zmienność kosztów zakupowych
- Value prop: powtarzalny standard decyzji zakupowych przekłada się bezpośrednio na marżę; kontrola nad wynikiem bez mikromanagementu
- Proof point: firmy z przygotowaniem negocjacyjnym blokują 30-50% proponowanych podwyżek dostawców — efekt widoczny w EBIT
- Frameworkowa obietnica: Tomasz Uściński + Profitia — 15 lat pomagamy firmom z branży [branża] ograniczać koszty związane z zakupami
- CTA: link Calendly https://calendly.com/profitia/zakupy-a-marza-firmy (15-min rozmowa o jednej kategorii kosztowej)
- Unikaj: szczegółów operacyjnych, listy modułów, "narzędzie zakupowe"

BRIDGE dla TIER 1 (KLUCZOWA ZASADA):
Most między artykułem a napięciem biznesowym musi być skoncentrowany na ORGANIZACJI i obszarze zakupów/warunków współpracy — NIE na roli odbiorcy jako osoby.
ZAKAZANE: "W Pana roli jako Prezes...", "Jako CEO musi Pan...", "Z Pana perspektywy jako zarząd..."
PREFEROWANE: "W takiej sytuacji w organizacji szczególnie ważne jest to, żeby wzrost nie tracił rentowności na poziomie warunków współpracy z dostawcami.", "Przy takiej skali to właśnie w obszarze zakupów i procurement najłatwiej zobaczyć, czy wzrost przekłada się na marżę.", "Kiedy firma tak rośnie, kwestia warunków z dostawcami staje się jednym z głównych driverów EBIT."

SOFT CTA DLA TIER 1 — WSZYSTKIE 3 KROKI (obowiązkowe):
Po Calendly i alternatywie telefonicznej dodaj soft-forward CTA jako ostatni element w każdym mailu (E1, FU1, FU2). Wording różny między krokami, sens identyczny: zachowaj lekką furtkę do przekazania do zakupów.

Email 1:
"Mam świadomość, że nie zajmuje się Pan bezpośrednio zakupami i warunkami współpracy z dostawcami - dlatego jeśli uzna Pan, że tak będzie lepiej, będę wdzięczny za przekazanie mojej wiadomości do Dyrektora Zakupów."

Follow-up 1:
"Jeśli w Pana organizacji tym obszarem zajmuje się ktoś z zakupów lub procurement, będę wdzięczny za przekazanie tej wiadomości dalej."

Follow-up 2:
"Jeśli uzna Pan, że to bardziej temat dla Dyrektora Zakupów, z góry dziękuję za przekazanie wiadomości."

Jeśli odbiorca jest kobietą (gender_form = "Pani"): zamł "Pan" → "Pani", "zajmuje się Pan" → "zajmuje się Pani", "uzna Pan" → "uzna Pani".
Ważne: ta reguła dotyczy TYLKO Tier 1. Wording FU1 i FU2 jest krótszy i prostszy niż E1.
""",
    "tier_2_procurement_management": """
Perspektywa TIER 2 — Procurement Management / Liderzy zakupów:
- Narracja: przygotowanie do negocjacji, standard pracy kupców, jakość argumentacji, cost drivers, should-cost, savings delivery
- Pain points: brak powtarzalnego standardu przygotowania do negocjacji, trudność uzasadnienia decyzji zarządowi, presja na wyniki savings, improwizacja przed negocjacjami
- Value prop: systematyczne przygotowanie każdej negocjacji (benchmark, cost drivers, analiza dostawcy, plan rozmowy) — nie jednorazowy projekt, ale trwały standard
- Proof point: kupcy z ustrukturyzowanym przygotowaniem osiągają 10-20% lepsze wyniki savings przy tych samych dostawcach
- Frameworkowa obietnica: Tomasz Uściński + Profitia — 15 lat pomagamy firmom z branży [branża] ograniczać koszty związane z zakupami
- CTA: link Calendly https://calendly.com/profitia/standard-negocjacji-i-oszczednosci (sprawdzenie podejścia na jednej kategorii)
- Unikaj: zbyt strategicznego języka zarządu, szczegółów technicznych platformy
""",
    "tier_3_buyers_operational": """
Perspektywa TIER 3 — Buyers / Category Managers / Operacyjni:
- Narracja: konkretne przygotowanie do rozmowy, argumentacja wobec dostawcy, ocena zasadności podwyżki, benchmark, cost drivers
- Pain points: brak pewności przed trudną negocjacją, za mało danych do obrony ceny, improwizacja zamiast struktury
- Value prop: pomoc przy jednej negocjacji — benchmark dostawcy, cost drivers, gotowy plan rozmowy
- CTA: link Calendly https://calendly.com/profitia/standard-negocjacji-i-oszczednosci
- Unikaj: języka strategicznego, ogólnych obietnic
""",
    "tier_uncertain": """
Perspektywa OGÓLNA (Tier nieustalony):
- Neutralny ton, skoncentrowany na problemie biznesowym
- Używaj języka procurement/zakupów bez zbędnego uszczegóławiania
- CTA: link Calendly https://calendly.com/profitia/standard-negocjacji-i-oszczednosci — miękkie, bez presji
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
    article_key_facts: str | None = '',
) -> str:
    """Wypełnia zmienne w szablonie promptu."""
    from datetime import datetime

    tier = contact.tier
    tier_label = contact.tier_label
    perspective = TIER_PERSPECTIVES.get(tier, TIER_PERSPECTIVES["tier_uncertain"])

    # Vocative + gender resolution from CSV dictionary (ZMIANA 5)
    try:
        from core.polish_names import resolve_polish_contact
        resolved = resolve_polish_contact(contact.first_name)
        gender = resolved["gender"]
        vocative = resolved["first_name_vocative"] or contact.first_name
        greeting = resolved["greeting"]
    except Exception:
        gender = "unknown"
        vocative = contact.first_name
        greeting = "Dzień dobry,"

    gender_form_map = {
        "male": "Pan (forma: Panu/Pana/Pan)",
        "female": "Pani (forma: Pani)",
    }
    gender_form = gender_form_map.get(gender, "neutralnie: Pani/Pana")

    # Article date
    pub_date = article.published_at or ""
    if pub_date and "T" in pub_date:
        pub_date = pub_date[:10]

    body_excerpt = (article.body or "")[:1500]

    replacements = {
        "{{vocative_first_name}}": vocative,
        "{{greeting}}": greeting,
        "{{last_name}}": contact.last_name,
        "{{job_title}}": contact.job_title,
        "{{company_name}}": contact.company_name,
        "{{tier_label}}": tier_label,
        "{{article_title}}": article.title,
        "{{article_source}}": _article_source_display(article),
        "{{article_date}}": pub_date,
        "{{article_url}}": article.canonical_url,
        "{{article_lead}}": article.lead or "",
        "{{article_body_excerpt}}": body_excerpt,
        "{{article_key_facts}}": article_key_facts or "",
        "{{tier_perspective}}": perspective.strip(),
        "{{gender_form}}": gender_form,
        "{{tier_calendly_link}}": CALENDLY_URLS.get(tier, CALENDLY_URLS["tier_uncertain"]),
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


def _article_source_display(article) -> str:
    """Zwraca przyjazną nazwę źródła artykułu — domenę z URL zamiast technicznego source_id.

    Np. 'portalspozywczy.pl' zamiast 'portal_spozywczy'.
    """
    from urllib.parse import urlparse
    url = getattr(article, "canonical_url", None) or getattr(article, "url", None) or ""
    if url:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower().lstrip("www.")
            if host:
                return host
        except Exception:
            pass
    # Fallback: source_id
    return getattr(article, "source_id", None) or "serwisu branżowego"


def _enforce_greeting(body: str, greeting: str) -> str:
    """Wymusza poprawne powitanie na początku każdego maila.

    Zasada: każdy mail MUSI zaczynać się dokładnie od '{greeting}' (np. 'Dzień dobry Panie Tadeuszu,').

    Obsługuje warianty LLM:
    - 'Panie X,\\n\\ntreść...'  → podmień pierwsze słowa na greeting
    - 'Panie X, treść na tej samej linii...' → podmień powitanie, dodaj \\n\\n przed treścią
    - 'Szanowny Panie X, treść...' → podmień powitanie
    - 'Dzień dobry,' (bez imienia) → podmień na pełne powitanie
    - Brak powitania → prepend
    """
    import re as _re

    if not greeting or not body:
        return body

    stripped = body.lstrip()

    # Już poprawne?
    if stripped.startswith(greeting):
        return body

    # Wzorzec powitania: opcjonalny "Szanown[ay] ", potem "Pani[e]? " + słowo, ewentualnie "Prezesie" itp.
    # albo "Dzień dobry" (z imię lub bez)
    GREETING_PATTERN = _re.compile(
        r'^(?:Szanown[ayi]\s+)?(?:Pani?e?\s+\w+|Pani\s+\w+|Panie\s+\w+)\s*,|'
        r'^Dzień dobry(?:\s+Pani?e?\s+\w+)?\s*,',
        _re.IGNORECASE | _re.UNICODE,
    )

    m = GREETING_PATTERN.match(stripped)
    if m:
        old_greeting_end = m.end()
        rest = stripped[old_greeting_end:]
        # Usuń wiodące spacje/newliny z reszty
        rest_stripped = rest.lstrip(" \t")
        # Dodaj separator — dwa newline jeśli brak
        if rest_stripped.startswith("\n"):
            sep = ""
        else:
            sep = "\n\n"
        return greeting + sep + rest_stripped
    else:
        # Brak rozpoznanego powitania — prepend
        return greeting + "\n\n" + stripped


# Technocratic phrases that indicate poor style — used in style check heuristic
_TECHNOCRATIC_PHRASES = [
    "precyzyjna ocena kosztu",
    "ryzyko marżowe",
    "przekłada się na pytanie o",
    "model rozwoju przekłada się",
    "przestrzeń do obrony wyniku",
    "uporządkować argumentację",
    "przewidywalność kosztów zakupowych",
    "mechanizmy rynkowe",
    "model funkcjonowania firmy",
    # Observation-tone violations (raportowy styl)
    "z artykułu wynika, że",
    "artykuł pokazuje, że",
    "w artykule opisano",
    "z tekstu wynika",
    "materiał wskazuje na",
]


def _check_style_issues(body: str, step_name: str, contact_name: str) -> None:
    """Loguje ostrzeżenie jeśli wygenerowany tekst zawiera technoKratyczne frazy."""
    body_lower = body.lower()
    hits = [p for p in _TECHNOCRATIC_PHRASES if p.lower() in body_lower]
    if hits:
        log.warning(
            "[StyleCheck] %s / %s — technoKratyczne frazy: %s",
            step_name, contact_name, ", ".join(f'\'{h}\'' for h in hits),
        )
    else:
        log.debug("[StyleCheck] %s / %s — OK", step_name, contact_name)


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
            "Piszesz naturalnie i lżej — krótsze zdania, prostsze słownictwo, mniej technokratyczny język. "
            "Mail ma brzmieć jak napisany po przeczytaniu artykułu, nie jak formalna analiza. "
            "KLUCZOWE: hipoteza i pierwsze akapity mają brzmieć jak osobista obserwacja po lekturze — NIE jak raport. "
            "ZAKAZANE: 'Z artykułu wynika, że', 'Artykuł pokazuje, że', 'Z tekstu wynika', 'W artykule opisano'. "
            "PREFEROWANE: 'Zwróciłem uwagę na to, że', 'Uderzyło mnie, że', 'Czytając ten artykuł, zwróciłem uwagę, że'. "
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
    source = _article_source_display(article)
    lead = article.lead or ""
    trigger_excerpt = lead[:200] if lead else title_str

    perspective_short = {
        "tier_1_c_level": "marży i odporności kosztowej firmy",
        "tier_2_procurement_management": "jakości przygotowania zespołu zakupowego",
        "tier_3_buyers_operational": "przygotowania do konkretnych negocjacji z dostawcami",
    }.get(tier, "efektywności zakupowej")

    calendly_url = CALENDLY_URLS.get(tier, CALENDLY_URLS["tier_uncertain"])
    cta_phone = "Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę śmiało przesłać numer - oddzwonię."

    # Soft-forward CTA dla Tier 1 (E1, FU1, FU2) — różny wording na każdy krok
    t1_forward_cta_e1 = ""
    t1_forward_cta_fu1 = ""
    t1_forward_cta_fu2 = ""
    if tier == "tier_1_c_level":
        t1_forward_cta_e1 = (
            "\nMam świadomość, że nie zajmuje się Pan bezpośrednio zakupami i warunkami "
            "współpracy z dostawcami - dlatego jeśli uzna Pan, że tak będzie lepiej, "
            "będę wdzięczny za przekazanie mojej wiadomości do Dyrektora Zakupów."
        )
        t1_forward_cta_fu1 = (
            "\nJeśli w Pana organizacji tym obszarem zajmuje się ktoś z zakupów lub procurement, "
            "będę wdzięczny za przekazanie tej wiadomości dalej."
        )
        t1_forward_cta_fu2 = (
            "\nJeśli uzna Pan, że to bardziej temat dla Dyrektora Zakupów, z góry dziękuję za przekazanie wiadomości."
        )

    # Uwaga: podpis NIE jest wstawiany — pochodzi z custom field pl_market_news_signature_tu
    body_1 = f"""Dzień dobry,

natknąłem się na artykuł w {source} dotyczący {trigger_excerpt[:150]}.

Zakładam, że z perspektywy {company} temat {perspective_short} jest istotny - szczególnie w kontekście negocjacji z dostawcami.

Nazywam się Tomasz Uściński i jestem z Profitii — polskiej firmy, która od 15 lat pomaga firmom z branży produkcyjnej i FMCG ograniczać koszty związane z zakupami.

Czy byłby Pan/Pani otwarty/a na krótką rozmowę? Tutaj można wybrać termin: {calendly_url}

{cta_phone}{t1_forward_cta_e1}"""

    body_2 = f"""Dzień dobry,

piszę ponownie w nawiązaniu do artykułu o {title_str[:80]}.

Jeden konkretny mechanizm, który może być istotny dla {company}: systematyczna weryfikacja zasadności proponowanych podwyżek od dostawców - zanim się na nie zgodzisz lub odrzucisz. Wiele firm traci kilka punktów procentowych marży rocznie z powodu braku danych do obrony ceny.

Tutaj można wybrać termin rozmowy: {calendly_url}

{cta_phone}{t1_forward_cta_fu1}"""

    body_3 = f"""Dzień dobry,

ostatnia wiadomość ode mnie. Jeśli temat negocjacji zakupowych jest aktualny dla {company} - chętnie pokażę przykład przygotowania do jednej negocjacji. Bez zobowiązań.

{calendly_url}

{cta_phone}{t1_forward_cta_fu2}"""

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

    # Resolve greeting once — used both in prompt and for post-processing enforcement
    try:
        from core.polish_names import resolve_polish_contact
        _resolved = resolve_polish_contact(contact.first_name)
        _greeting = _resolved["greeting"]
    except Exception:
        _greeting = "Dzień dobry,"

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
    def _enrich_step(step: dict, step_name: str = "") -> dict:
        body = step.get("body", "")

        # NIE wstawiaj podpisu do body — podpis pochodzi z Apollo custom field pl_market_news_signature_tu
        # SIGNATURE_PLAIN zostawiony jako stała tylko dla fallback heurystyki

        # TWARDA REGUŁA: każdy mail musi zaczynać się od poprawnego powitania
        body = _enforce_greeting(body, _greeting)
        if body != step.get("body", "") and step_name:
            log.debug("[Greeting] Corrected greeting in %s for %s → '%s'",
                      step_name, contact.full_name, _greeting)

        # Walidacja liczby słów (log ostrzeżenie — nie blokuje)
        if step_name and step_name in WORD_COUNT_LIMITS:
            word_count = len(body.split())
            lo, hi = WORD_COUNT_LIMITS[step_name]
            if word_count < lo or word_count > hi:
                log.warning(
                    "[WordCount] %s: %d words (expected %d-%d) for %s",
                    step_name, word_count, lo, hi, contact.full_name,
                )
            else:
                log.debug("[WordCount] %s: %d words OK (%d-%d)", step_name, word_count, lo, hi)

        # Sprawdzenie stylistyczne (log ostrzeżenie — nie blokuje)
        if step_name and body:
            _check_style_issues(body, step_name, contact.full_name)

        return {
            "subject": step.get("subject", ""),
            "body": body,
            "body_html": _body_to_html(body),
            "body_core": body,  # for Apollo custom fields
        }

    return OutreachPack(
        email_1=_enrich_step(result.get("email_1", {}), "email_1"),
        follow_up_1=_enrich_step(result.get("follow_up_1", {}), "follow_up_1"),
        follow_up_2=_enrich_step(result.get("follow_up_2", {}), "follow_up_2"),
        review_notes=result.get("review_notes", {}),
        tier=tier,
        tier_label=tier_label,
        contact_email=contact.email,
        contact_name=contact.full_name,
        generated_by=generated_by,
    )
