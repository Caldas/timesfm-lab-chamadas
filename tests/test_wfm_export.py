from io import BytesIO

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("scipy")
openpyxl = pytest.importorskip("openpyxl")

from callcenter_lab.wfm import (
    Scenario,
    StaffingConfig,
    build_plan,
    build_plan_range,
    build_workbook,
    optimize_roster,
    run_scenarios,
    sensitivity,
)
from callcenter_lab.wfm.scheduling import RosterRules, example_templates


@pytest.fixture(scope="module")
def results():
    index = pd.date_range("2024-03-04", periods=96, freq="30min")
    hours = index.hour + index.minute / 60
    point = pd.Series(np.where((hours >= 8) & (hours < 20), 40.0, 0.0), index=index)
    config = StaffingConfig(cost_per_hour=20)
    plan = build_plan(point, config)
    return {
        "config": config,
        "plan": plan,
        "plan_range": build_plan_range(point, point * 0.8, point * 1.3, config),
        "roster": optimize_roster(plan["scheduled"], example_templates(), 30, RosterRules(default_cost_per_hour=20)),
        "scenarios": run_scenarios({"expected": point, "low": point * 0.8, "high": point * 1.3},
                                   [Scenario("Base"), Scenario("Volume alto", volume="high")], config),
        "sensitivity": sensitivity(point, config, "aht_factor"),
    }


def open_workbook(data: bytes):
    return openpyxl.load_workbook(BytesIO(data))


def test_full_workbook_has_one_sheet_per_result(results):
    book = open_workbook(build_workbook(**results))
    assert book.sheetnames == [
        "Resumo", "Configuração", "Dimensionamento", "Por dia", "Faixa de volume",
        "Escala - turnos", "Escala - pausas", "Escala - cobertura", "Cenários", "Sensibilidade",
    ]


def test_plan_sheet_has_readable_headers_and_the_right_numbers(results):
    sheet = open_workbook(build_workbook(**results))["Dimensionamento"]
    headers = [c.value for c in sheet[1]]
    assert headers[:3] == ["Intervalo", "Chamadas", "TMA (s)"] and "Agentes" in headers
    column = headers.index("Agentes") + 1
    agents = [sheet.cell(row=r, column=column).value for r in range(2, sheet.max_row + 1)]
    assert agents == results["plan"]["agents"].tolist()
    assert sheet.freeze_panes == "A2" and sheet["A1"].font.bold


def test_summary_sheet_has_the_key_figures_and_the_notice(results):
    sheet = open_workbook(build_workbook(**results))["Resumo"]
    rows = {sheet.cell(row=r, column=1).value: sheet.cell(row=r, column=2).value for r in range(2, sheet.max_row + 1)}
    assert "laboratório de estudo" in rows["Aviso"]
    assert rows["Pico de agentes"] == int(results["plan"]["agents"].max())
    assert rows["Escala: pessoas necessárias (headcount)"] == results["roster"].headcount
    assert rows["Cenários comparados"] == 2


def test_only_the_given_results_become_sheets(results):
    book = open_workbook(build_workbook(plan=results["plan"]))
    assert book.sheetnames == ["Resumo", "Dimensionamento"]
    assert open_workbook(build_workbook()).sheetnames == ["Resumo"]


def test_scenarios_and_roster_sheets_carry_their_data(results):
    book = open_workbook(build_workbook(**results))
    scenario_sheet = book["Cenários"]
    assert [scenario_sheet.cell(row=r, column=1).value for r in (2, 3)] == ["Base", "Volume alto"]
    shifts = book["Escala - turnos"]
    assert shifts.max_row - 1 == len(results["roster"].shifts)
    config_sheet = book["Configuração"]
    names = [config_sheet.cell(row=r, column=1).value for r in range(2, config_sheet.max_row + 1)]
    assert "Meta de nível de serviço (%)" in names and "Shrinkage total (%)" in names
