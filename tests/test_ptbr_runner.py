"""Invariantes do runner do benchmark pt-BR."""

import pytest

from benchmarks.ptbr import runner


class FakeNeedleAgent:
    def __init__(self):
        self.queries = []

    def reset(self):
        pass

    def complete(self, query):
        self.queries.append(query)
        if query == "quebra utf-8":
            raise RuntimeError("UnicodeDecodeError: invalid continuation byte")
        return {"function_calls": [], "confidence": None}


class FakeResetFailsOnceAgent(FakeNeedleAgent):
    def __init__(self):
        super().__init__()
        self.reset_calls = 0

    def reset(self):
        self.reset_calls += 1
        if self.reset_calls == 1:
            raise RuntimeError("Needle worker exited unexpectedly")


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


def test_run_arm_records_inference_error_and_continues(monkeypatch):
    fake_agent = FakeNeedleAgent()
    monkeypatch.setattr(runner, "_agent", lambda *args, **kwargs: fake_agent)
    cases = [
        {"query": "quebra utf-8", "calls": [], "category": "irrelevant"},
        {"query": "continua", "calls": [], "category": "irrelevant"},
    ]

    result = runner.run_arm("pt/en", [], "", cases)

    assert fake_agent.queries == ["quebra utf-8", "continua"]
    assert result["records"][0]["ok"] is False
    assert "UnicodeDecodeError" in result["records"][0]["error"]
    assert result["records"][1]["ok"] is True
    assert result["records"][1]["error"] is None


def test_run_arm_records_reset_error_and_continues(monkeypatch):
    fake_agent = FakeResetFailsOnceAgent()
    monkeypatch.setattr(runner, "_agent", lambda *args, **kwargs: fake_agent)
    cases = [
        {"query": "primeiro", "calls": [], "category": "irrelevant"},
        {"query": "segundo", "calls": [], "category": "irrelevant"},
    ]

    result = runner.run_arm("pt/en", [], "", cases)

    assert result["records"][0]["ok"] is False
    assert "worker exited" in result["records"][0]["error"]
    assert result["records"][1]["ok"] is True
