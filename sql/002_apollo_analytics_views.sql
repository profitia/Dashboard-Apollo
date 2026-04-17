-- 002_apollo_analytics_views.sql
-- Widoki analityczne dla Apollo outreach dashboard.
-- Nie modyfikuje istniejących tabel - tylko CREATE OR REPLACE VIEW.

-- ============================================================
-- v_sequence_performance — metryki per sekwencja
-- ============================================================
CREATE OR REPLACE VIEW apollo.v_sequence_performance AS
SELECT
    s.apollo_sequence_id,
    s.sequence_name,
    s.status                    AS sequence_status,
    s.campaign_slug,
    s.campaign_type,
    s.persona,
    s.industry,
    count(*)                                                        AS messages_count,
    count(*) FILTER (WHERE m.is_delivered IS TRUE)                  AS delivered_count,
    count(*) FILTER (WHERE m.is_opened IS TRUE)                     AS opened_count,
    count(*) FILTER (WHERE m.is_clicked IS TRUE)                    AS clicked_count,
    count(*) FILTER (WHERE m.is_replied IS TRUE)                    AS replied_count,
    count(*) FILTER (WHERE m.is_positive_reply IS TRUE)             AS positive_reply_count,
    count(*) FILTER (WHERE m.is_unsubscribed IS TRUE)               AS unsubscribed_count,
    count(*) FILTER (WHERE m.is_bounced IS TRUE)                    AS bounced_count,
    count(*) FILTER (WHERE m.is_spam_blocked IS TRUE)               AS spam_blocked_count,
    count(*) FILTER (WHERE m.status = 'failed')                     AS failed_count,
    count(*) FILTER (WHERE m.status = 'completed')                  AS completed_count,
    ROUND(count(*) FILTER (WHERE m.is_opened IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS open_rate,
    ROUND(count(*) FILTER (WHERE m.is_clicked IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS click_rate,
    ROUND(count(*) FILTER (WHERE m.is_replied IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS reply_rate,
    ROUND(count(*) FILTER (WHERE m.is_positive_reply IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS positive_reply_rate,
    ROUND(count(*) FILTER (WHERE m.is_bounced IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS bounce_rate,
    ROUND(count(*) FILTER (WHERE m.is_unsubscribed IS TRUE)::numeric
        / NULLIF(count(*), 0), 4)                                   AS unsubscribe_rate
FROM apollo.outreach_messages m
LEFT JOIN apollo.sequences s
    ON s.apollo_sequence_id = m.apollo_sequence_id
GROUP BY
    s.apollo_sequence_id,
    s.sequence_name,
    s.status,
    s.campaign_slug,
    s.campaign_type,
    s.persona,
    s.industry;

-- ============================================================
-- v_message_status_summary — rozkład statusów wiadomości
-- ============================================================
CREATE OR REPLACE VIEW apollo.v_message_status_summary AS
SELECT
    m.status,
    count(*)                                                        AS messages_count,
    ROUND(count(*)::numeric / NULLIF(SUM(count(*)) OVER (), 0), 4) AS pct
FROM apollo.outreach_messages m
GROUP BY m.status
ORDER BY messages_count DESC;

-- ============================================================
-- v_reply_type_summary — rozkład typów odpowiedzi
-- ============================================================
CREATE OR REPLACE VIEW apollo.v_reply_type_summary AS
SELECT
    m.reply_type,
    count(*)                                                        AS messages_count,
    ROUND(count(*)::numeric / NULLIF(SUM(count(*)) OVER (), 0), 4) AS pct
FROM apollo.outreach_messages m
GROUP BY m.reply_type
ORDER BY messages_count DESC;

-- ============================================================
-- v_sequence_status_summary — wiadomości wg statusu sekwencji
-- ============================================================
CREATE OR REPLACE VIEW apollo.v_sequence_status_summary AS
SELECT
    COALESCE(s.status, 'no_sequence_match')                         AS sequence_status,
    count(*)                                                        AS messages_count,
    ROUND(count(*)::numeric / NULLIF(SUM(count(*)) OVER (), 0), 4) AS pct
FROM apollo.outreach_messages m
LEFT JOIN apollo.sequences s
    ON s.apollo_sequence_id = m.apollo_sequence_id
GROUP BY COALESCE(s.status, 'no_sequence_match')
ORDER BY messages_count DESC;
