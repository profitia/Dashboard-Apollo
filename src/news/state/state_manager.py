"""
State Manager — zarządza stanami przetworzonych artykułów i sekwencji.

Odpowiada za:
- Deduplikację artykułów (article hash / URL)
- Deduplikację firm (ta sama firma w oknie czasu)
- Rejestr sekwencji (sequence_key → sequence_id)
- Statusy artykułów: patrz news.pipeline_status.PipelineStatus

Stałe STATUS_* są aliasami na PipelineStatus — jedyne źródło prawdy o statusach.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from news.pipeline_status import PipelineStatus, REPROCESSABLE_STATUSES

log = logging.getLogger(__name__)


class ArticleStateManager:
    """Zarządza stanem przetworzonych artykułów."""

    # Status constants — aliasy na PipelineStatus (jedyne źródło prawdy)
    STATUS_DISCOVERED = "discovered"  # stan przejściowy (nie finalny)
    STATUS_SCORING_FAILED = PipelineStatus.REJECTED_QUALIFICATION
    STATUS_NO_COMPANY = PipelineStatus.BLOCKED_COMPANY_NOT_FOUND
    STATUS_NO_CONTACTS = PipelineStatus.BLOCKED_NO_EMAIL
    STATUS_ARTICLE_QUALIFIED_BUT_NO_CONTACTS = PipelineStatus.BLOCKED_NO_CONTACT
    STATUS_PENDING_REVIEW = PipelineStatus.PENDING_MANUAL_REVIEW
    STATUS_SEQUENCE_CREATED = PipelineStatus.READY_FOR_REVIEW
    STATUS_EXCLUDED = PipelineStatus.BLOCKED_COMPANY_EXCLUDED

    def __init__(self, state_file: str, sequences_log_file: str):
        self.state_file = state_file
        self.sequences_log_file = sequences_log_file
        self._articles: dict[str, dict] = {}
        self._sequences: dict[str, dict] = {}
        self._load()

    def _load(self):
        """Ładuje stan z plików JSON."""
        for path, attr in [(self.state_file, "_articles"), (self.sequences_log_file, "_sequences")]:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        setattr(self, attr, json.load(f))
                    log.debug("Loaded state from %s (%d entries)", path, len(getattr(self, attr)))
                except Exception as exc:
                    log.warning("Could not load state file %s: %s", path, exc)

    def _save_articles(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._articles, f, indent=2, ensure_ascii=False)

    def _save_sequences(self):
        os.makedirs(os.path.dirname(self.sequences_log_file), exist_ok=True)
        with open(self.sequences_log_file, "w", encoding="utf-8") as f:
            json.dump(self._sequences, f, indent=2, ensure_ascii=False)

    def is_article_processed(self, url: str, article_hash: str | None = None) -> bool:
        """Sprawdza czy artykuł był już przetworzony (w dowolnym statusie końcowym).

        Statusy w REPROCESSABLE_STATUSES (np. PENDING_MANUAL_REVIEW, stary "pending_review")
        NIE są traktowane jako przetworzone — pipeline może ponowić te case'y.
        """
        canonical_url = url.split("?")[0].rstrip("/")
        if canonical_url in self._articles:
            status = self._articles[canonical_url].get("status", "")
            if status and status not in REPROCESSABLE_STATUSES:
                return True
        if article_hash and article_hash in self._articles:
            status = self._articles[article_hash].get("status", "")
            return bool(status and status not in REPROCESSABLE_STATUSES)
        return False

    def is_company_in_cooldown(
        self,
        company_normalized: str,
        dedup_window_days: int = 30,
    ) -> bool:
        """Sprawdza czy firma ma aktywną sekwencję w oknie deduplikacji."""
        now = datetime.now(timezone.utc)
        for key, seq in self._sequences.items():
            if seq.get("company_normalized") == company_normalized:
                created_str = seq.get("created_at", "")
                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str)
                        if (now - created).days < dedup_window_days:
                            log.info(
                                "Company '%s' in cooldown — sequence '%s' created %s days ago",
                                company_normalized,
                                seq.get("sequence_name"),
                                (now - created).days,
                            )
                            return True
                    except ValueError:
                        pass
        return False

    def mark_article(
        self,
        url: str,
        article_hash: str,
        status: str,
        metadata: dict | None = None,
    ):
        """Zapisuje status artykułu."""
        canonical_url = url.split("?")[0].rstrip("/")
        entry = {
            "url": url,
            "canonical_url": canonical_url,
            "article_hash": article_hash,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            entry.update(metadata)
        self._articles[canonical_url] = entry
        self._save_articles()

    def register_sequence(
        self,
        sequence_name: str,
        sequence_id: str | None,
        article_url: str,
        article_title: str,
        company_name: str,
        company_normalized: str,
        contacts_count: int,
        tier_breakdown: dict,
    ):
        """Rejestruje nowo utworzoną sekwencję."""
        key = sequence_name
        self._sequences[key] = {
            "sequence_name": sequence_name,
            "sequence_id": sequence_id,
            "article_url": article_url,
            "article_title": article_title,
            "company_name": company_name,
            "company_normalized": company_normalized,
            "contacts_count": contacts_count,
            "tier_breakdown": tier_breakdown,
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_sequences()

    def get_all_sequences(self) -> list[dict]:
        return list(self._sequences.values())

    def get_recent_sequences(self, days: int = 7) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = []
        for seq in self._sequences.values():
            created_str = seq.get("created_at", "")
            try:
                created = datetime.fromisoformat(created_str)
                if created >= cutoff:
                    result.append(seq)
            except (ValueError, TypeError):
                pass
        return sorted(result, key=lambda s: s.get("created_at", ""), reverse=True)
