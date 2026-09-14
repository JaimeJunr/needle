"""Invariantes do runner do benchmark pt-BR."""

import pytest

from benchmarks.ptbr import runner


def test_gate_drops_low_confidence_calls():
    got = [{"name": "control_lights", "arguments": {}}]
    kept, gated = runner.apply_gate(got, 0.1, 0.4)
    assert kept == [] and gated is True


def test_gate_keeps_confident_calls():
    got = [{"name": "control_lights", "arguments": {}}]
    kept, gated = runner.apply_gate(got, 0.9, 0.4)
    assert kept == got and gated is False


def test_gate_is_inapplicable_when_confidence_is_none():
    """Modelo tunado nao tem cabeca de confianca calibrada: confidence vem None.

    Tratar None como 0.0 gatearia tudo e produziria um score falsamente zero;
    tratar como 1.0 deixaria o gate silenciosamente inoperante. O correto e
    nao gatear E sinalizar que o gate nao se aplica, para o relatorio nao
    comparar macas com laranjas.
    """
    got = [{"name": "control_lights", "arguments": {}}]
    kept, gated = runner.apply_gate(got, None, 0.4)
    assert kept == got
    assert gated is False


def test_gate_without_threshold_keeps_everything():
    got = [{"name": "control_lights", "arguments": {}}]
    assert runner.apply_gate(got, 0.0, 0.0) == (got, False)


def test_summary_reports_confidence_as_unavailable():
    result = {"arm": "pt/en", "seconds": 1.0, "min_confidence": 0.4, "records": [
        {"category": "positive", "phenomenon": None, "critical": False,
         "confidence": None, "gated": False, "ok": True},
    ]}
    summary = runner.summarise(result)
    assert summary["mean_confidence"] is None
    assert summary["gate_applicable"] is False


def test_summary_reports_confidence_when_available():
    result = {"arm": "en/en", "seconds": 1.0, "min_confidence": 0.0, "records": [
        {"category": "positive", "phenomenon": None, "critical": False,
         "confidence": 0.5, "gated": False, "ok": True},
    ]}
    summary = runner.summarise(result)
    assert summary["mean_confidence"] == 0.5
    assert summary["gate_applicable"] is True
