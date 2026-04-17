import requests
from config import APOLLO_API_KEY, APOLLO_BASE_URL


class ApolloClient:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": APOLLO_API_KEY,
        }
        self._custom_fields_cache = None
        self._load_custom_fields()

    def _load_custom_fields(self):
        """Pobiera definicje custom fields z Apollo i buduje mapowania nazwa↔ID."""
        data = self._get("typed_custom_fields")
        fields = data.get("typed_custom_fields", [])
        self._custom_fields_cache = {
            "by_name": {f["name"]: f["id"] for f in fields},
            "by_id": {f["id"]: f["name"] for f in fields},
        }

    @property
    def custom_fields(self):
        """Lazy-loaded mapowanie custom fields (nazwa→ID i ID→nazwa)."""
        if self._custom_fields_cache is None:
            self._load_custom_fields()
        return self._custom_fields_cache

    def resolve_custom_fields(self, contact):
        """Zamienia typed_custom_fields kontaktu z {ID: wartość} na {nazwa: wartość}."""
        raw = contact.get("typed_custom_fields", {})
        if not raw:
            return {}
        by_id = self.custom_fields["by_id"]
        return {by_id.get(field_id, field_id): value for field_id, value in raw.items()}

    def get_custom_field_id(self, field_name):
        """Zwraca ID custom field po nazwie (lub None)."""
        return self.custom_fields["by_name"].get(field_name)

    def refresh_custom_fields(self):
        """Wymusza ponowne pobranie definicji custom fields z Apollo."""
        self._custom_fields_cache = None

    def _post(self, endpoint, payload=None):
        if payload is None:
            payload = {}
        resp = requests.post(f"{APOLLO_BASE_URL}/{endpoint}", json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def _get(self, endpoint, params=None):
        if params is None:
            params = {}
        resp = requests.get(f"{APOLLO_BASE_URL}/{endpoint}", params=params, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def get_sequences(self):
        """Pobiera listę sekwencji (emailer campaigns) z Apollo."""
        data = self._post("emailer_campaigns/search", {"page": 1, "per_page": 50})
        return data.get("emailer_campaigns", [])

    def get_sequence_contacts(self, sequence_id, statuses=None):
        """
        Pobiera kontakty z danej sekwencji filtrowane wg statusu.
        statuses: lista np. ['replied', 'interested', 'meeting_booked']
        """
        payload = {
            "emailer_campaign_id": sequence_id,
            "page": 1,
            "per_page": 100,
        }
        if statuses:
            payload["contact_statuses"] = statuses

        data = self._post("emailer_campaigns/contacts", payload)
        return data.get("contacts", [])

    def get_engaged_contacts(self, sequence_id):
        """Pobiera kontakty, które odpowiedziały lub są zainteresowane."""
        return self.get_sequence_contacts(
            sequence_id,
            statuses=["replied", "interested"]
        )

    def search_contact(self, email):
        """Szuka kontaktu w Apollo po e-mailu."""
        data = self._post("contacts/search", {
            "q_keywords": email,
            "page": 1,
            "per_page": 1,
        })
        contacts = data.get("contacts", [])
        return contacts[0] if contacts else None

    def create_opportunity(self, contact_id, name, amount=None):
        """Tworzy deal/opportunity w Apollo powiązany z kontaktem."""
        payload = {
            "opportunity": {
                "name": name,
                "contact_ids": [contact_id],
                "status": "open",
            }
        }
        if amount:
            payload["opportunity"]["amount"] = amount
        return self._post("opportunities", payload)

    def get_contact_details(self, contact_id):
        """Pobiera szczegóły kontaktu z Apollo."""
        return self._get(f"contacts/{contact_id}")

    # ── People Search (prospecting) ──────────────────────────────

    def search_people(self, person_titles=None, person_locations=None,
                      person_seniorities=None, organization_locations=None,
                      q_keywords=None, organization_num_employees_ranges=None,
                      currently_using_any_of_technology_uids=None,
                      q_organization_domains_list=None,
                      page=1, per_page=25):
        """
        Wyszukuje nowych prospectów w bazie Apollo (nie zużywa kredytów).
        Endpoint: POST /api/v1/mixed_people/api_search
        """
        payload = {"page": page, "per_page": per_page}
        if person_titles:
            payload["person_titles"] = person_titles
        if person_locations:
            payload["person_locations"] = person_locations
        if person_seniorities:
            payload["person_seniorities"] = person_seniorities
        if organization_locations:
            payload["organization_locations"] = organization_locations
        if q_keywords:
            payload["q_keywords"] = q_keywords
        if organization_num_employees_ranges:
            payload["organization_num_employees_ranges"] = organization_num_employees_ranges
        if currently_using_any_of_technology_uids:
            payload["currently_using_any_of_technology_uids"] = currently_using_any_of_technology_uids
        if q_organization_domains_list:
            payload["q_organization_domains_list"] = q_organization_domains_list

        resp = requests.post(
            f"{APOLLO_BASE_URL.replace('/v1', '')}/api/v1/mixed_people/api_search",
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("people", []), data.get("total_entries", 0)

    # ── People Enrichment ────────────────────────────────────────

    def enrich_person(self, linkedin_url=None, email=None, first_name=None,
                      last_name=None, domain=None, organization_name=None,
                      apollo_id=None):
        """
        Wzbogaca dane osoby (po LinkedIn URL, email, nazwisku+domenie itp.).
        Zużywa kredyty. Zwraca pełny profil z linkedin_url, employment_history itp.
        """
        payload = {}
        if apollo_id:
            payload["id"] = apollo_id
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        if email:
            payload["email"] = email
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if domain:
            payload["domain"] = domain
        if organization_name:
            payload["organization_name"] = organization_name

        resp = requests.post(
            f"{APOLLO_BASE_URL.replace('/v1', '')}/api/v1/people/match",
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        return resp.json().get("person")

    # ── News Articles Search (triggery) ──────────────────────────

    def search_news(self, organization_ids, categories=None,
                    published_at_min=None, published_at_max=None,
                    page=1, per_page=25):
        """
        Szuka artykułów/newsów powiązanych z firmami (hires, investment, contract...).
        Zużywa kredyty.
        """
        payload = {
            "organization_ids": organization_ids,
            "page": page,
            "per_page": per_page,
        }
        if categories:
            payload["categories"] = categories
        if published_at_min:
            payload["published_at"] = payload.get("published_at", {})
            payload["published_at"]["min"] = published_at_min
        if published_at_max:
            payload["published_at"] = payload.get("published_at", {})
            payload["published_at"]["max"] = published_at_max

        resp = requests.post(
            f"{APOLLO_BASE_URL.replace('/v1', '')}/api/v1/news_articles/search",
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("news_articles", []), data.get("pagination", {})

    # ── Organization Search ──────────────────────────────────────

    def search_organizations(self, q_keywords=None, organization_locations=None,
                             page=1, per_page=25):
        """Szuka firm w bazie Apollo po nazwie/słowach kluczowych."""
        payload = {"page": page, "per_page": per_page}
        if q_keywords:
            payload["q_organization_name"] = q_keywords
        if organization_locations:
            payload["organization_locations"] = organization_locations

        data = self._post("mixed_companies/search", payload)
        return data.get("organizations", []), data.get("pagination", {})

    # ── Add to Sequence ──────────────────────────────────────────

    def add_to_sequence(self, sequence_id, contact_ids, email_account_id=None):
        """
        Dodaje kontakty do sekwencji Apollo.
        contact_ids: lista Apollo contact IDs
        email_account_id: (opcjonalny) ID konta email do wysyłki
        """
        payload = {
            "contact_ids": contact_ids,
            "emailer_campaign_id": sequence_id,
        }
        if email_account_id:
            payload["email_account_id"] = email_account_id

        return self._post("emailer_campaigns/add_contact_ids", payload)
