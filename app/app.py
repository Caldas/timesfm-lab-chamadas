"""Interface Streamlit do laboratório TimesFM para dados de tráfego.

Run with: streamlit run app/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from trafego_lab.backtest import run_backtest
from trafego_lab.dados import detect_columns, load_csv, prepare_series, resample_series
from trafego_lab.modelo import choose_backend, forecast, load_forecaster

ROOT = Path(__file__).resolve().parent.parent
# label -> (pandas frequency, season length in steps)
FREQUENCIES = {"15 minutos": ("15min", 96), "Hora": ("h", 24), "Dia": ("D", 7)}

st.set_page_config(page_title="TimesFM Lab — Tráfego", page_icon="🚦", layout="wide")


@st.cache_resource(show_spinner="Carregando o TimesFM 3.0 (na primeira vez baixa os pesos)...")
def get_forecaster(backend: str):
    return load_forecaster(backend)


def available_files() -> list[Path]:
    found = sorted((ROOT / "data" / "samples").glob("*.csv"))
    found += sorted((ROOT / "data" / "raw").rglob("*.csv"))
    return found


def plot_forecast(history, point=None, lower=None, upper=None, actual=None, baseline=None):
    fig = go.Figure()
    fig.add_scatter(x=history.index, y=history.values, name="Histórico", line={"color": "#555"})
    if actual is not None:
        fig.add_scatter(x=actual.index, y=actual.values, name="Real", line={"color": "#000"})
    if upper is not None:
        fig.add_scatter(x=upper.index, y=upper.values, line={"width": 0}, showlegend=False)
        fig.add_scatter(
            x=lower.index,
            y=lower.values,
            fill="tonexty",
            fillcolor="rgba(31,119,180,0.2)",
            line={"width": 0},
            name="Faixa 10%–90%",
        )
    if baseline is not None:
        fig.add_scatter(
            x=baseline.index, y=baseline.values, name="Repetir ciclo anterior",
            line={"dash": "dot", "color": "#999"},
        )
    if point is not None:
        fig.add_scatter(x=point.index, y=point.values, name="Previsão TimesFM",
                        line={"color": "#1f77b4", "width": 3})
    fig.update_layout(height=450, margin={"l": 10, "r": 10, "t": 10, "b": 10},
                      legend={"orientation": "h"})
    return fig


st.title("🚦 TimesFM Lab — Tráfego")
st.caption("Laboratório de estudo. Não use os resultados para decisões de engenharia.")

# ---------------------------------------------------------------- 1. dados
with st.sidebar:
    st.header("1. Dados")
    upload = st.file_uploader("Enviar um CSV", type=["csv"])
    files = available_files()
    choice = None
    if upload is None:
        if files:
            choice = st.selectbox("…ou escolher um arquivo", files, format_func=lambda p: p.name)
        else:
            st.info("Nenhum arquivo em data/samples. Envie um CSV.")

if upload is None and choice is None:
    st.stop()

try:
    df = load_csv(upload if upload is not None else str(choice))
except Exception as exc:  # noqa: BLE001 - show any read problem to the user
    st.error(f"Não consegui ler o arquivo: {exc}")
    st.stop()

with st.sidebar:
    guess_date, guess_value = detect_columns(df)
    cols = list(df.columns)
    date_col = st.selectbox("Coluna de data/hora", cols, index=cols.index(guess_date)
                            if guess_date in cols else 0)
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])] or cols
    value_col = st.selectbox("Coluna de volume", numeric_cols, index=numeric_cols.index(guess_value)
                             if guess_value in numeric_cols else 0)

    # Some datasets mix several sites (e.g. one row per junction); let the user pick one.
    filter_options = [
        c for c in cols if c not in (date_col, value_col) and 1 < df[c].nunique() <= 20
    ]
    filter_col = st.selectbox("Filtrar por (opcional)", ["(nenhum)"] + filter_options,
                              help="Útil quando o arquivo tem vários cruzamentos/pontos.")
    if filter_col != "(nenhum)":
        filter_value = st.selectbox(f"Valor de {filter_col}", sorted(df[filter_col].unique()))
        df = df[df[filter_col] == filter_value]

    st.header("2. Parâmetros")
    freq_label = st.selectbox("Agrupar por", list(FREQUENCIES), index=1)
    how_label = st.radio("Como agrupar", ["Somar (contagens)", "Média (velocidade, taxa)"])
    horizon = st.slider("Quantos passos prever", 6, 336, 48)
    max_history = st.slider("Quanto histórico usar (passos)", 48, 4000, 1000, step=24)
    backend = st.selectbox("Motor", ["auto", "mlx", "torch"], help="auto = MLX no Mac Apple silicon")

freq, season = FREQUENCIES[freq_label]
how = "sum" if how_label.startswith("Somar") else "mean"

try:
    series = resample_series(prepare_series(df, date_col, value_col), freq, how)
except Exception as exc:  # noqa: BLE001
    st.error(f"Problema nos dados: {exc}")
    st.stop()
series = series.iloc[-max_history:]

st.subheader("Série preparada")
c1, c2, c3 = st.columns(3)
c1.metric("Pontos", len(series))
c2.metric("Início", f"{series.index[0]:%Y-%m-%d %H:%M}")
c3.metric("Fim", f"{series.index[-1]:%Y-%m-%d %H:%M}")
st.plotly_chart(plot_forecast(series), width="stretch")
chosen_backend = choose_backend(backend)
st.caption(f"Motor que será usado: **{chosen_backend}**")
if chosen_backend == "torch":
    st.info("Motor PyTorch (CPU): a previsão pode ser mais lenta que no Apple silicon. "
            "Para acelerar, reduza o histórico e o número de passos na barra lateral.")

tab_forecast, tab_backtest = st.tabs(["🔮 Previsão", "🧪 Teste de realidade"])

# ------------------------------------------------------------- 2. previsão
with tab_forecast:
    st.write("Prevê os próximos passos depois do fim da série.")
    if st.button("Prever", type="primary"):
        model = get_forecaster(backend)
        with st.spinner("Calculando..."):
            result = forecast(model, series.to_numpy(), horizon)
        future = pd.date_range(series.index[-1], periods=horizon + 1, freq=freq)[1:]
        point, lower, upper = (pd.Series(v, index=future)
                               for v in (result.point, result.lower, result.upper))
        tail = series.iloc[-horizon * 3:]
        st.plotly_chart(plot_forecast(tail, point, lower, upper), width="stretch")
        st.caption("A faixa azul mostra onde o modelo espera que o valor fique em 80% dos casos.")
        st.download_button(
            "Baixar previsão (CSV)",
            pd.DataFrame({"previsao": point, "min_10pct": lower, "max_90pct": upper})
            .rename_axis("timestamp").to_csv().encode(),
            file_name="previsao.csv",
        )

# -------------------------------------------------------------- 3. backtest
with tab_backtest:
    st.write("Esconde o final da série, prevê só com o que veio antes e compara com o que aconteceu.")
    if st.button("Rodar teste de realidade"):
        if horizon >= len(series) // 2:
            st.warning("Reduza o horizonte ou aumente o histórico: restaria pouco dado para o modelo.")
        else:
            model = get_forecaster(backend)
            with st.spinner("Calculando..."):
                bt = run_backtest(series, horizon, lambda h, n: forecast(model, h, n), season)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Erro médio (MAE)", f"{bt.mae:,.1f}")
            m2.metric("Erro percentual (MAPE)", f"{bt.mape:.1f}%")
            m3.metric("Dentro da faixa 10–90%", f"{bt.coverage:.0%}")
            m4.metric("MAE de 'repetir ciclo'", f"{bt.baseline_mae:,.1f}",
                      delta=f"{bt.mae - bt.baseline_mae:+,.1f}", delta_color="inverse")
            tail = bt.history.iloc[-horizon * 3:]
            st.plotly_chart(
                plot_forecast(tail, bt.point, bt.lower, bt.upper, bt.actual, bt.baseline),
                width="stretch",
            )
            st.caption(
                "Se o MAE do TimesFM for menor que o de 'repetir o ciclo anterior', o modelo está "
                "agregando valor. Se a cobertura ficar muito abaixo de 80%, a faixa está otimista."
            )
