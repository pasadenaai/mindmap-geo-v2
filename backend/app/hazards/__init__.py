"""Hazard-event ingest: normalized model, adapter interface and per-source parsers.

Design: docs/HAZARD_ALERTS_DESIGN.md. Parsers are pure functions over raw payloads so they
can be tested against recorded fixtures; network access lives only in `HazardAdapter.fetch`.
"""
