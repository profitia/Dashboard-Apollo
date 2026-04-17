#!/usr/bin/env python3
"""
Apollo → Pipedrive Agent

Przepływ:
1. Pobiera sekwencje z Apollo
2. Użytkownik wybiera sekwencję
3. Pobiera kontakty, które odpowiedziały / są zainteresowane
4. Dla każdego kontaktu:
   a) Tworzy osobę + deal w Pipedrive (jeśli nie istnieje)
   b) Tworzy opportunity (deal) w Apollo
5. Wyświetla podsumowanie

Prospecting:
- Szukanie prospectów w Apollo (People Search)
- Wzbogacanie danych po LinkedIn URL / email (People Enrichment)
- Monitorowanie newsów firmowych jako triggerów (News Articles)
- Dodawanie kontaktów do sekwencji outreach
"""

from apollo_client import ApolloClient
from pipedrive_client import PipedriveClient


def select_sequence(apollo):
    """Pozwala użytkownikowi wybrać sekwencję z listy."""
    print("\n📋 Pobieranie sekwencji z Apollo...")
    sequences = apollo.get_sequences()

    if not sequences:
        print("❌ Brak sekwencji w Apollo.")
        return None

    print(f"\nZnaleziono {len(sequences)} sekwencji:\n")
    for i, seq in enumerate(sequences, 1):
        active = "🟢" if seq.get("active") else "⚪"
        print(f"  {i}. {active} {seq.get('name', 'Bez nazwy')} (ID: {seq['id']})")

    while True:
        choice = input(f"\nWybierz numer sekwencji (1-{len(sequences)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(sequences):
            return sequences[int(choice) - 1]
        print("Nieprawidłowy wybór, spróbuj ponownie.")


def process_contact(contact, apollo, pipedrive, stats):
    """Przetwarza pojedynczy kontakt — tworzy rekordy w Pipedrive i Apollo."""
    email = contact.get("email")
    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    org_name = contact.get("organization", {}).get("name") if contact.get("organization") else None
    phone = contact.get("phone_numbers", [{}])[0].get("sanitized_number") if contact.get("phone_numbers") else None
    apollo_contact_id = contact.get("id")

    if not email:
        print(f"  ⚠️  {name} — brak e-maila, pomijam")
        stats["skipped"] += 1
        return

    # --- Pipedrive ---
    existing = pipedrive.search_person(email)
    if existing:
        person_id = existing["id"]
        print(f"  ℹ️  {name} ({email}) — już istnieje w Pipedrive (ID: {person_id})")
        stats["existed"] += 1
    else:
        person = pipedrive.create_person(name, email, org_name=org_name, phone=phone)
        person_id = person["id"]
        print(f"  ✅ {name} ({email}) — utworzono osobę w Pipedrive (ID: {person_id})")
        stats["created_pipedrive"] += 1

    # Deal w Pipedrive
    deal_title = f"Outreach — {name}"
    deal = pipedrive.create_deal(deal_title, person_id)
    print(f"       → Deal w Pipedrive: \"{deal['title']}\" (ID: {deal['id']})")
    stats["deals_pipedrive"] += 1

    # --- Apollo Opportunity ---
    if apollo_contact_id:
        opp = apollo.create_opportunity(apollo_contact_id, deal_title)
        opp_id = opp.get("opportunity", {}).get("id", "?")
        print(f"       → Opportunity w Apollo (ID: {opp_id})")
        stats["deals_apollo"] += 1


def prospecting_menu(apollo):
    """Podmenu: Prospecting przez Apollo (Search, Enrich, News, Add to Sequence)."""
    while True:
        print("\n" + "=" * 50)
        print("  🔎 Prospecting (Apollo)")
        print("=" * 50)
        print("  1. 🔍 Szukaj prospectów (People Search)")
        print("  2. 🧩 Wzbogać kontakt (LinkedIn URL / email)")
        print("  3. 📰 News / triggery firmowe")
        print("  4. 🏢 Szukaj firm (Organization Search)")
        print("  5. ➕ Dodaj kontakty do sekwencji")
        print("  0. ↩  Powrót")

        choice = input("\nWybór: ").strip()

        if choice == "1":
            _people_search(apollo)
        elif choice == "2":
            _enrich_person(apollo)
        elif choice == "3":
            _news_search(apollo)
        elif choice == "4":
            _org_search(apollo)
        elif choice == "5":
            _add_to_sequence(apollo)
        elif choice == "0":
            return
        else:
            print("Nieprawidłowy wybór.")


def _people_search(apollo):
    """Interaktywne szukanie prospectów w bazie Apollo."""
    print("\n🔍 People Search — filtry (Enter = pomiń)")

    titles_raw = input("  Stanowiska (np. Dyrektor Zakupów, Category Manager): ").strip()
    seniorities_raw = input("  Seniority [owner/founder/c_suite/vp/head/director/manager/senior]: ").strip()
    org_locations_raw = input("  Lokalizacja firmy (np. Poland, Warsaw): ").strip()
    keywords = input("  Słowa kluczowe: ").strip()
    employees_raw = input("  Wielkość firmy (np. 50,200): ").strip()

    titles = [t.strip() for t in titles_raw.split(",")] if titles_raw else None
    seniorities = [s.strip() for s in seniorities_raw.split(",")] if seniorities_raw else None
    org_locations = [l.strip() for l in org_locations_raw.split(",")] if org_locations_raw else None
    emp_ranges = [employees_raw] if employees_raw else None

    print("\n⏳ Szukam...")
    people, total = apollo.search_people(
        person_titles=titles,
        person_seniorities=seniorities,
        organization_locations=org_locations,
        q_keywords=keywords or None,
        organization_num_employees_ranges=emp_ranges,
    )

    print(f"\n📊 Znaleziono {total} wyników (pokazuję {len(people)}):\n")
    for i, p in enumerate(people, 1):
        name = f"{p.get('first_name', '')} {p.get('last_name_obfuscated', '')}".strip()
        title = p.get("title", "—")
        org = p.get("organization", {}).get("name", "—") if p.get("organization") else "—"
        has_email = "✉️" if p.get("has_email") else "  "
        print(f"  {i:>3}. {has_email} {name} — {title} @ {org}")

    if not people:
        return

    # Opcja enrichmentu
    enrich = input("\nWzbogacić któryś kontakt? Podaj numer (lub Enter = pomiń): ").strip()
    if enrich.isdigit() and 1 <= int(enrich) <= len(people):
        person = people[int(enrich) - 1]
        _enrich_by_apollo_id(apollo, person["id"])


def _enrich_person(apollo):
    """Wzbogaca dane kontaktu po LinkedIn URL lub email."""
    print("\n🧩 People Enrichment — podaj dane do wyszukania:")
    linkedin_url = input("  LinkedIn URL (np. linkedin.com/in/jan-kowalski): ").strip() or None
    email = input("  Email: ").strip() or None
    first_name = input("  Imię: ").strip() or None
    last_name = input("  Nazwisko: ").strip() or None
    domain = input("  Domena firmy (np. firma.pl): ").strip() or None

    if not any([linkedin_url, email, first_name]):
        print("⚠️  Podaj przynajmniej LinkedIn URL, email, lub imię+nazwisko+domenę.")
        return

    print("\n⏳ Wzbogacam dane...")
    person = apollo.enrich_person(
        linkedin_url=linkedin_url,
        email=email,
        first_name=first_name,
        last_name=last_name,
        domain=domain,
    )

    if not person:
        print("❌ Nie znaleziono dopasowania w Apollo.")
        return

    _print_enriched_person(person)


def _enrich_by_apollo_id(apollo, apollo_id):
    """Wzbogaca kontakt po Apollo ID."""
    print("\n⏳ Wzbogacam dane...")
    person = apollo.enrich_person(apollo_id=apollo_id)
    if not person:
        print("❌ Nie udało się wzbogacić kontaktu.")
        return
    _print_enriched_person(person)


def _print_enriched_person(person):
    """Wyświetla wzbogacone dane osoby."""
    print(f"\n  ✅ {person.get('name', '?')}")
    print(f"     Stanowisko:  {person.get('title', '—')}")
    print(f"     Firma:       {person.get('headline', '—')}")
    print(f"     Email:       {person.get('email', '—')} ({person.get('email_status', '?')})")
    print(f"     LinkedIn:    {person.get('linkedin_url', '—')}")
    print(f"     Twitter:     {person.get('twitter_url', '—')}")
    print(f"     Miasto:      {person.get('city', '—')}, {person.get('country', '—')}")

    org = person.get("organization")
    if org:
        print(f"\n     🏢 Firma: {org.get('name', '—')}")
        print(f"        Branża:      {org.get('industry', '—')}")
        print(f"        Pracownicy:  {org.get('estimated_num_employees', '—')}")
        print(f"        Przychód:    {org.get('annual_revenue_printed', '—')}")
        print(f"        Funding:     {org.get('total_funding_printed', '—')}")

    history = person.get("employment_history", [])
    if history:
        print(f"\n     📋 Historia zatrudnienia ({len(history)} pozycji):")
        for h in history[:5]:
            current = " (obecne)" if h.get("current") else ""
            print(f"        • {h.get('title', '?')} @ {h.get('organization_name', '?')}{current}")


def _news_search(apollo):
    """Szuka newsów firmowych jako triggerów outreach."""
    print("\n📰 News Articles Search")
    org_query = input("  Nazwa firmy do wyszukania: ").strip()
    if not org_query:
        return

    # Najpierw znajdź firmę
    print("  ⏳ Szukam firmy...")
    orgs, _ = apollo.search_organizations(q_keywords=org_query)
    if not orgs:
        print("  ❌ Nie znaleziono firmy.")
        return

    print(f"\n  Znalezione firmy:")
    for i, org in enumerate(orgs[:10], 1):
        print(f"    {i}. {org.get('name', '?')} — {org.get('website_url', '—')}")

    org_choice = input(f"\n  Wybierz firmę (1-{min(len(orgs), 10)}): ").strip()
    if not org_choice.isdigit() or not (1 <= int(org_choice) <= min(len(orgs), 10)):
        return

    org_id = orgs[int(org_choice) - 1].get("id")
    categories_raw = input("  Kategorie [hires/investment/contract] (Enter = wszystkie): ").strip()
    categories = [c.strip() for c in categories_raw.split(",")] if categories_raw else None

    print("\n  ⏳ Szukam newsów...")
    articles, pagination = apollo.search_news(
        organization_ids=[org_id],
        categories=categories,
    )

    total = pagination.get("total_entries", len(articles))
    print(f"\n  📰 Znaleziono {total} artykułów:\n")
    for i, art in enumerate(articles[:20], 1):
        date = art.get("published_at", "—")[:10]
        cats = ", ".join(art.get("event_categories", []))
        print(f"    {i}. [{date}] [{cats}] {art.get('title', '—')}")
        snippet = art.get("snippet", "")
        if snippet:
            print(f"       {snippet[:150]}...")
        print(f"       🔗 {art.get('url', '—')}")


def _org_search(apollo):
    """Szuka firm w bazie Apollo."""
    print("\n🏢 Organization Search")
    query = input("  Nazwa firmy / słowa kluczowe: ").strip()
    location = input("  Lokalizacja (Enter = dowolna): ").strip()

    if not query:
        return

    print("\n  ⏳ Szukam...")
    orgs, pagination = apollo.search_organizations(
        q_keywords=query,
        organization_locations=[location] if location else None,
    )

    total = pagination.get("total_entries", len(orgs))
    print(f"\n  Znaleziono {total} firm (pokazuję {len(orgs)}):\n")
    for i, org in enumerate(orgs[:25], 1):
        name = org.get("name", "?")
        website = org.get("website_url", "—")
        industry = org.get("industry", "—")
        employees = org.get("estimated_num_employees", "—")
        print(f"    {i}. {name} | {industry} | {employees} prac. | {website}")


def _add_to_sequence(apollo):
    """Dodaje kontakty do sekwencji Apollo."""
    print("\n➕ Dodaj kontakty do sekwencji")

    # Wybierz sekwencję
    sequence = select_sequence(apollo)
    if not sequence:
        return

    contact_ids_raw = input("\n  Podaj Apollo Contact IDs (oddzielone przecinkami): ").strip()
    if not contact_ids_raw:
        print("  Anulowano.")
        return

    contact_ids = [cid.strip() for cid in contact_ids_raw.split(",")]

    print(f"\n  ⏳ Dodaję {len(contact_ids)} kontaktów do sekwencji \"{sequence.get('name')}\"...")
    try:
        result = apollo.add_to_sequence(sequence["id"], contact_ids)
        print(f"  ✅ Dodano! Odpowiedź: {result}")
    except Exception as e:
        print(f"  ❌ Błąd: {e}")


def main():
    print("=" * 50)
    print("  Apollo → Pipedrive Agent")
    print("=" * 50)

    apollo = ApolloClient()
    pipedrive = PipedriveClient()

    while True:
        print("\n" + "=" * 50)
        print("  Menu główne")
        print("=" * 50)
        print("  1. 📋 Apollo → Pipedrive (przetwórz sekwencję)")
        print("  2. 🔎 Prospecting (szukaj, wzbogacaj, triggery)")
        print("  0. ❌ Wyjście")

        choice = input("\nWybór: ").strip()

        if choice == "1":
            run_apollo_pipedrive_flow(apollo, pipedrive)
        elif choice == "2":
            prospecting_menu(apollo)
        elif choice == "0":
            print("Do zobaczenia!")
            return
        else:
            print("Nieprawidłowy wybór.")


def run_apollo_pipedrive_flow(apollo, pipedrive):
    """Oryginalny flow: Apollo sekwencja → Pipedrive."""
    # 1. Wybierz sekwencję
    sequence = select_sequence(apollo)
    if not sequence:
        return

    seq_name = sequence.get("name", "Bez nazwy")
    seq_id = sequence["id"]
    print(f"\n🎯 Wybrana sekwencja: {seq_name}")

    # 2. Pobierz zaangażowane kontakty
    print("\n🔍 Pobieranie kontaktów (replied / interested)...")
    contacts = apollo.get_engaged_contacts(seq_id)

    if not contacts:
        print("ℹ️  Brak kontaktów z odpowiedzią w tej sekwencji.")
        return

    print(f"Znaleziono {len(contacts)} kontaktów.\n")

    # 3. Potwierdzenie
    confirm = input(f"Przetworzyć {len(contacts)} kontaktów? (t/n): ").strip().lower()
    if confirm not in ("t", "tak", "y", "yes"):
        print("Anulowano.")
        return

    # 4. Przetwarzanie
    stats = {
        "created_pipedrive": 0,
        "existed": 0,
        "skipped": 0,
        "deals_pipedrive": 0,
        "deals_apollo": 0,
    }

    print("\n" + "-" * 50)
    for contact in contacts:
        try:
            process_contact(contact, apollo, pipedrive, stats)
        except Exception as e:
            name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
            print(f"  ❌ Błąd przy {name}: {e}")
            stats["skipped"] += 1
    print("-" * 50)

    # 5. Podsumowanie
    print(f"""
📊 Podsumowanie:
   Nowe osoby w Pipedrive:   {stats['created_pipedrive']}
   Już istniejące:           {stats['existed']}
   Deale w Pipedrive:        {stats['deals_pipedrive']}
   Opportunity w Apollo:     {stats['deals_apollo']}
   Pominięte/błędy:          {stats['skipped']}
""")


if __name__ == "__main__":
    main()
