import requests
from config import PIPEDRIVE_API_TOKEN, PIPEDRIVE_BASE_URL, PIPEDRIVE_PIPELINE_ID, PIPEDRIVE_STAGE_ID


class PipedriveClient:
    def __init__(self):
        self.token = PIPEDRIVE_API_TOKEN
        self.base_url = PIPEDRIVE_BASE_URL

    def _url(self, endpoint):
        return f"{self.base_url}/{endpoint}"

    def _params(self):
        return {"api_token": self.token}

    def search_person(self, email):
        """Szuka osoby w Pipedrive po e-mailu."""
        resp = requests.get(
            self._url("persons/search"),
            params={**self._params(), "term": email, "fields": "email"},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        return items[0]["item"] if items else None

    def create_person(self, name, email, org_name=None, phone=None):
        """Tworzy osobę w Pipedrive."""
        payload = {
            "name": name,
            "email": [email],
        }
        if phone:
            payload["phone"] = [phone]
        if org_name:
            payload["org_id"] = self._get_or_create_org(org_name)

        resp = requests.post(
            self._url("persons"),
            params=self._params(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def _get_or_create_org(self, org_name):
        """Szuka organizacji lub tworzy nową."""
        resp = requests.get(
            self._url("organizations/search"),
            params={**self._params(), "term": org_name},
        )
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("items", [])
        if items:
            return items[0]["item"]["id"]

        resp = requests.post(
            self._url("organizations"),
            params=self._params(),
            json={"name": org_name},
        )
        resp.raise_for_status()
        return resp.json()["data"]["id"]

    def create_deal(self, title, person_id, org_id=None):
        """Tworzy deal w Pipedrive powiązany z osobą."""
        payload = {
            "title": title,
            "person_id": person_id,
        }
        if org_id:
            payload["org_id"] = org_id
        if PIPEDRIVE_PIPELINE_ID:
            payload["pipeline_id"] = int(PIPEDRIVE_PIPELINE_ID)
        if PIPEDRIVE_STAGE_ID:
            payload["stage_id"] = int(PIPEDRIVE_STAGE_ID)

        resp = requests.post(
            self._url("deals"),
            params=self._params(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def get_pipelines(self):
        """Pobiera listę pipeline'ów — pomocne do uzupełnienia .env."""
        resp = requests.get(self._url("pipelines"), params=self._params())
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_stages(self, pipeline_id=None):
        """Pobiera etapy (stages) — pomocne do uzupełnienia .env."""
        params = self._params()
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        resp = requests.get(self._url("stages"), params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])
