"""Public call-center datasets: what they are, where they come from, how to fetch and convert them.

Every dataset is converted to the same simple CSV (``timestamp`` and ``calls_offered``, on a
regular grid with zeros for empty intervals) so the app and the notebooks can read any of them.
Nothing here is redistributed in the repository: the files are downloaded on demand into
``data/raw/<id>/`` together with a ``SOURCE.md`` carrying the attribution.
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

USER_AGENT = "callcenter-lab/0.1 (+https://github.com/Caldas/timesfm-lab-chamadas)"
Fetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    summary: str
    source_url: str
    license: str
    attribution: str
    granularity: str
    period: str
    approx_size: str
    downloadable: bool = True


REGISTRY: dict[str, Dataset] = {
    "synthetic": Dataset(
        id="synthetic",
        title="Chamadas sintéticas (geradas)",
        summary="Chamadas por 30 min de uma central fictícia (seg-sex 8h-20h, sáb 8h-14h, dom fechado).",
        source_url="https://github.com/Caldas/timesfm-lab-chamadas",
        license="MIT (gerado por este projeto)",
        attribution="Gerado por scripts/gerar_amostra.py",
        granularity="30 minutos",
        period="12 semanas a partir de 2024-03-04",
        approx_size="~80 KB",
        downloadable=False,
    ),
    "synthetic-service": Dataset(
        id="synthetic-service",
        title="Atendimento sintético (gerado pelo simulador)",
        summary="Como o relatório de uma central: chamadas, atendidas, abandonos, TMA, espera e nível de serviço por 30 min, saída do simulador.",
        source_url="https://github.com/Caldas/timesfm-lab-chamadas",
        license="MIT (gerado por este projeto)",
        attribution="Gerado por scripts/gerar_amostra.py com o simulador de callcenter_lab.wfm",
        granularity="30 minutos",
        period="12 semanas a partir de 2024-03-04",
        approx_size="~350 KB",
        downloadable=False,
    ),
    "synthetic-events": Dataset(
        id="synthetic-events",
        title="Chamadas sintéticas com feriados e campanhas (gerado)",
        summary="As mesmas 12 semanas, com dois feriados (volume 0,3x) e três campanhas (1,5x), e o calendário de eventos correspondente.",
        source_url="https://github.com/Caldas/timesfm-lab-chamadas",
        license="MIT (gerado por este projeto)",
        attribution="Gerado por scripts/gerar_amostra.py",
        granularity="30 minutos",
        period="12 semanas a partir de 2024-03-04",
        approx_size="~90 KB",
        downloadable=False,
    ),
    "synthetic-queues": Dataset(
        id="synthetic-queues",
        title="Três filas sintéticas: vendas, suporte e cobrança (gerado)",
        summary="Chamadas por 30 min de três filas com formatos e tamanhos diferentes, em um arquivo com coluna de fila.",
        source_url="https://github.com/Caldas/timesfm-lab-chamadas",
        license="MIT (gerado por este projeto)",
        attribution="Gerado por scripts/gerar_amostra.py",
        granularity="30 minutos",
        period="12 semanas a partir de 2024-03-04",
        approx_size="~380 KB",
        downloadable=False,
    ),
    "technion-bank": Dataset(
        id="technion-bank",
        title="Banco anônimo de Israel (Technion / Mandelbaum)",
        summary="Uma chamada por linha numa central de banco, 12 meses de 1999; agregado por 30 min com chamadas, atendidas, abandonos, TMA, espera e nível de serviço.",
        source_url="https://www.math-stat.unibe.ch/studium/skripten_und_lehrmaterial/datensaetze_imsv/callcenter/index_ger.html",
        license="Sem licença formal: livre para uso, citando a fonte e avisando o Prof. Avi Mandelbaum",
        attribution=(
            "Dados da central telefônica do 'Anonymous Bank' (Israel), fornecidos por Ilan Guedj e "
            "Avi Mandelbaum (Technion SEE Center); espelho da Universidade de Berna. "
            "Se usar em publicação, cite a fonte e avise avim@ie.technion.ac.il."
        ),
        granularity="30 minutos (agregado)",
        period="1999-01-01 a 1999-12-31",
        approx_size="~12 MB baixados, ~35 KB de CSV",
    ),
    "hyndman-bank": Dataset(
        id="hyndman-bank",
        title="Banco norte-americano (Hyndman)",
        summary="Chegadas de chamadas a cada 5 min, dias úteis das 7h às 21h, de um grande banco comercial.",
        source_url="https://robjhyndman.com/data/callcenter.txt",
        license="Não declarada no arquivo; o pacote R 'stR' que o inclui é GPL-3",
        attribution=(
            "Arquivo de Rob J. Hyndman (robjhyndman.com/data/callcenter.txt). Citação: De Livera, "
            "Hyndman & Snyder (2011), Forecasting time series with complex seasonal patterns using "
            "exponential smoothing, JASA 106(496), 1513-1527."
        ),
        granularity="5 minutos",
        period="a partir de 2003-03-03 (dias úteis)",
        approx_size="~110 KB baixados",
    ),
    "nyc-311": Dataset(
        id="nyc-311",
        title="NYC 311 Call Center Inquiry (Nova York)",
        summary="Todas as chamadas atendidas por agente na linha 311; agregadas por hora no servidor.",
        source_url="https://data.cityofnewyork.us/City-Government/311-Call-Center-Inquiry/wewp-mm3p",
        license="Não informada na página do dataset; dados abertos da cidade de Nova York (veja os termos do NYC Open Data)",
        attribution="NYC 311 Call Center Inquiry, NYC Open Data (data.cityofnewyork.us, id wewp-mm3p).",
        granularity="1 hora (agregado)",
        period="2016-2019 por padrão (opções --nyc-ano-inicio / --nyc-ano-fim); após mar/2020 o dado não representa todas as chamadas",
        approx_size="~1 MB de CSV para 4 anos (o original tem ~105 milhões de linhas)",
    ),
}
DOWNLOADABLE = [d.id for d in REGISTRY.values() if d.downloadable]

# --- Technion files (University of Bern mirror) ------------------------------------------------
BERN_BASE = (
    "https://www.math-stat.unibe.ch/unibe/portal/fak_naturwis/a_dept_math/a_dept_ms/"
    "content/e237483/e237655/e237803/e237840/e237842/"
)
TECHNION_FILES = {
    "January": "files237844",
    "February": "files237845",
    "March": "files237846",
    "April": "files237847",
    "May": "files285545",
    "June": "files237848",
    "July": "files237849",
    "August": "files237850",
    "September": "files237851",
    "October": "files237852",
    "November": "files237853",
    "December": "files237854",
}
HYNDMAN_URL = "https://robjhyndman.com/data/callcenter.txt"
NYC_RESOURCE = "https://data.cityofnewyork.us/resource/wewp-mm3p.json"


# --- Conversion: raw files -> regular series of calls offered ----------------------------------
def counts_from_timestamps(timestamps, freq: str = "30min") -> pd.DataFrame:
    """Count events (one per call) per interval, on a regular grid with zeros for empty slots."""
    index = pd.DatetimeIndex(pd.to_datetime(list(timestamps))).sort_values()
    counts = pd.Series(1, index=index).resample(freq).sum()
    return pd.DataFrame({"timestamp": counts.index, "calls_offered": counts.to_numpy().astype(int)})


def parse_technion_calls(text: str) -> pd.DataFrame:
    """One monthly Technion file -> one row per call: arrival time, outcome, queue wait and handling time.

    Fields used: ``date`` + ``vru_entry`` (arrival), ``outcome`` (AGENT = answered by an agent,
    HANG = the caller hung up, PHANTOM = a third class the dataset reports separately),
    ``q_time`` (seconds in the queue) and ``ser_time`` (seconds with the agent).
    """
    # The header has one name fewer than the rows (R wrote row numbers), so pandas uses the first
    # column as the index on its own; do not pass index_col.
    df = pd.read_csv(io.StringIO(text), sep="	")
    day = pd.to_datetime(df["date"].astype(str).str.zfill(6), format="%y%m%d", errors="coerce")
    clock = pd.to_timedelta(df["vru_entry"].astype(str), errors="coerce")
    calls = pd.DataFrame(
        {
            "timestamp": day + clock,
            "outcome": df["outcome"].astype(str).str.strip().str.upper(),
            "wait_seconds": pd.to_numeric(df["q_time"], errors="coerce"),
            "handle_seconds": pd.to_numeric(df["ser_time"], errors="coerce"),
        }
    )
    return calls.dropna(subset=["timestamp"]).reset_index(drop=True)


def parse_technion_month(text: str) -> pd.DatetimeIndex:
    """Arrival time of every call in one monthly Technion file."""
    return pd.DatetimeIndex(parse_technion_calls(text)["timestamp"])


def aggregate_service_data(calls: pd.DataFrame, freq: str = "30min", threshold_seconds: float = 20.0) -> pd.DataFrame:
    """Per-call rows -> the per-interval table a call-center report gives.

    Columns: ``calls_offered`` (all calls), ``calls_answered`` (outcome AGENT), ``calls_abandoned``
    (HANG), ``calls_other`` (anything else, e.g. PHANTOM), ``aht_seconds`` and ``avg_wait_seconds``
    (mean over answered calls) and ``service_level_pct`` (answered within the threshold / offered).
    Intervals without calls have zero counts and empty (NaN) averages.
    """
    frame = calls.copy()
    frame["answered"] = frame["outcome"] == "AGENT"
    frame["abandoned"] = frame["outcome"] == "HANG"
    frame["within"] = frame["answered"] & (frame["wait_seconds"] <= threshold_seconds)
    frame["handle_answered"] = frame["handle_seconds"].where(frame["answered"])
    frame["wait_answered"] = frame["wait_seconds"].where(frame["answered"])
    grouped = frame.set_index("timestamp").sort_index().resample(freq)
    offered = grouped.size()
    answered = grouped["answered"].sum()
    abandoned = grouped["abandoned"].sum()
    within = grouped["within"].sum()
    out = pd.DataFrame(
        {
            "timestamp": offered.index,
            "calls_offered": offered.to_numpy().astype(int),
            "calls_answered": answered.to_numpy().astype(int),
            "calls_abandoned": abandoned.to_numpy().astype(int),
            "calls_other": (offered - answered - abandoned).to_numpy().astype(int),
            "aht_seconds": grouped["handle_answered"].mean().to_numpy().round(1),
            "avg_wait_seconds": grouped["wait_answered"].mean().to_numpy().round(1),
            "service_level_pct": (100 * within / offered.where(offered > 0)).to_numpy().round(1),
        }
    )
    return out


def parse_hyndman(text: str) -> pd.DataFrame:
    """Hyndman's file is a grid: a header row of dates, then one row per 5-minute slot (from 7:00)."""
    rows = [[cell.strip() for cell in line.split("\t")] for line in text.splitlines() if line.strip()]
    dates = pd.to_datetime([cell for cell in rows[0][1:] if cell], format="%d/%m/%Y")
    slots = rows[1:]  # each row: a time label such as "7:05", then one value per day
    offsets = [pd.to_timedelta(row[0] + ":00") for row in slots]
    grid = np.array([[float(x) for x in row[1 : 1 + len(dates)]] for row in slots])  # slots x days
    stamps = [day + offset for day in dates for offset in offsets]
    frame = pd.DataFrame({"timestamp": stamps, "calls_offered": grid.T.reshape(-1)})
    regular = frame.set_index("timestamp")["calls_offered"].resample("5min").sum(min_count=1).fillna(0)
    return pd.DataFrame({"timestamp": regular.index, "calls_offered": regular.to_numpy().astype(int)})


def parse_nyc_hourly(rows: list[dict]) -> pd.DataFrame:
    """Rows from the Socrata query (day, hour, calls) -> hourly series with zeros for empty hours."""
    frame = pd.DataFrame(rows)
    stamp = pd.to_datetime(frame["day"]) + pd.to_timedelta(frame["hour"].astype(int), unit="h")
    series = pd.Series(frame["calls"].astype(int).to_numpy(), index=stamp).sort_index()
    regular = series.resample("h").sum(min_count=1).fillna(0)
    return pd.DataFrame({"timestamp": regular.index, "calls_offered": regular.to_numpy().astype(int)})


# --- Download ----------------------------------------------------------------------------------
def http_get(url: str, retries: int = 2, timeout: int = 120) -> bytes:
    """GET a URL with a few retries; raises RuntimeError with a readable message on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Falha ao baixar {url}: {last}")


def _cached(path: Path, url: str, fetch: Fetcher, force: bool) -> bytes:
    if path.exists() and not force:
        return path.read_bytes()
    data = fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def write_source_note(dataset: Dataset, folder: Path) -> None:
    """Write SOURCE.md next to the data, so the attribution always travels with the files."""
    note = (
        f"# {dataset.title}\n\n"
        f"- Fonte: {dataset.source_url}\n"
        f"- Licença/condições: {dataset.license}\n"
        f"- Atribuição: {dataset.attribution}\n"
        f"- Granularidade: {dataset.granularity}\n"
        f"- Período: {dataset.period}\n\n"
        "Arquivo gerado por `scripts/baixar_datasets.py`. Colunas: `timestamp`, `calls_offered`.\n"
    )
    (folder / "SOURCE.md").write_text(note, encoding="utf-8")


def download_dataset(
    dataset_id: str,
    out_root: Path,
    *,
    force: bool = False,
    fetch: Fetcher = http_get,
    nyc_years: tuple[int, int] = (2016, 2019),
    log: Callable[[str], None] = print,
) -> Path:
    """Download one dataset, convert it, and return the path of the resulting CSV.

    Raw files are cached in ``<out_root>/<id>/_raw`` so a re-run does not hit the network again
    (use ``force=True`` to download again).
    """
    if dataset_id not in DOWNLOADABLE:
        raise KeyError(dataset_id)
    dataset = REGISTRY[dataset_id]
    folder = out_root / dataset_id
    csv_path = folder / f"{dataset_id}.csv"
    if csv_path.exists() and not force:
        log(f"[REUSO] {dataset_id}: já existe em {csv_path}")
        return csv_path
    raw = folder / "_raw"

    if dataset_id == "technion-bank":
        monthly: list[pd.DataFrame] = []
        for month, file_id in TECHNION_FILES.items():
            log(f"[INFO] technion-bank: {month} ...")
            blob = _cached(raw / f"{month}.txt.zip", f"{BERN_BASE}{file_id}/{month}.txt_ger.zip", fetch, force)
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                text = archive.read(archive.namelist()[0]).decode("latin-1")
            monthly.append(parse_technion_calls(text))
        result = aggregate_service_data(pd.concat(monthly, ignore_index=True), "30min")
    elif dataset_id == "hyndman-bank":
        log("[INFO] hyndman-bank: baixando ...")
        blob = _cached(raw / "callcenter.txt", HYNDMAN_URL, fetch, force)
        result = parse_hyndman(blob.decode("utf-8", errors="replace"))
    else:  # nyc-311
        start, end = nyc_years
        frames = []
        for year in range(start, end + 1):
            log(f"[INFO] nyc-311: {year} (agregando por hora no servidor) ...")
            query = {
                "$select": "date_trunc_ymd(date_time) as day, date_extract_hh(date_time) as hour, count(*) as calls",
                "$where": f"date_time between '{year}-01-01T00:00:00' and '{year}-12-31T23:59:59'",
                "$group": "day,hour",
                "$order": "day,hour",
                "$limit": "50000",
            }
            url = f"{NYC_RESOURCE}?{urllib.parse.urlencode(query)}"
            blob = _cached(raw / f"{year}.json", url, fetch, force)
            frames.append(parse_nyc_hourly(json.loads(blob)))
        merged = pd.concat(frames).set_index("timestamp")["calls_offered"].sort_index()
        regular = merged.resample("h").sum(min_count=1).fillna(0)
        result = pd.DataFrame({"timestamp": regular.index, "calls_offered": regular.to_numpy().astype(int)})

    folder.mkdir(parents=True, exist_ok=True)
    result.to_csv(csv_path, index=False)
    write_source_note(dataset, folder)
    log(f"[OK] {dataset_id}: {len(result)} intervalos em {csv_path}")
    return csv_path
