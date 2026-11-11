"""FarmTech Solutions - Fase 3 - Pessoa B: graficos e correlacao.

Le o CSV tratado entregue pela Pessoa A e gera, na pasta de saida:
  1_evolucao_umidade_ph.png        evolucao no tempo (bruto x media movel)
  2_zoom_bruto_vs_suavizado.png    primeiros 3 dias, onde esta a coleta Wokwi
  3_umidade_vs_bomba.png           umidade, limiar de 50% e acionamentos
  4_distribuicoes_sensores.png     distribuicao de cada sensor
  5_agua_e_horas_ligadas.png       tempo de bomba ligada e agua estimada
  6_correlacao_heatmap.png         matriz de correlacao (completo x so Wokwi)
  correlacao_com_bomba.csv         correlacoes de cada variavel com a bomba

Uso:
  python graficos_correlacao.py
  python graficos_correlacao.py --entrada resultados/leituras_tratadas.csv --saida graficos

Atencao: 98,75% das linhas sao sinteticas (simulado = 1). Os graficos
descrevem o processamento, nao o comportamento de uma fazenda real.
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

# Fronteira entre coleta do Wokwi e complemento em Python (ver README da Pessoa A).
FRONTEIRA = pd.Timestamp("2026-01-02 03:00:00")
LIMIAR_UMIDADE = 50  # regra do firmware: bomba liga com umidade < 50 e sem chuva prevista
COR_BRUTO, COR_SUAVE, COR_BOMBA = "#9bb7d4", "#c0392b", "#f2b134"
VARIAVEIS = ["umidade", "ph", "fosforo", "potassio", "nitrogenio", "bomba"]
ROTULOS = {"umidade": "Umidade", "ph": "pH", "fosforo": "Fósforo (P)",
           "potassio": "Potássio (K)", "nitrogenio": "Nitrogênio (N)",
           "bomba": "Bomba"}


def carregar(caminho):
    """Carrega o CSV tratado e converte a coluna de data/hora."""
    df = pd.read_csv(caminho, parse_dates=["data_hora"])
    df["origem"] = np.where(df["simulado"] == 0, "Wokwi (coletado)", "Python (sintético)")
    return df


def salvar(fig, pasta, nome):
    fig.savefig(pasta / nome, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("gerado:", pasta / nome)


def marcar_fronteira(ax):
    """Linha vertical que separa dados coletados de dados sinteticos."""
    ax.axvline(FRONTEIRA, color="gray", ls="--", lw=1)


def grafico_evolucao(df, pasta):
    """Grafico 1: evolucao de umidade e pH nos 90 dias (bruto x media movel)."""
    fig, eixos = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for ax, col, rot in [(eixos[0], "umidade", "Umidade (%)"),
                         (eixos[1], "ph", "pH (escala fictícia)")]:
        ax.plot(df.data_hora, df[f"{col}_original"], color=COR_BRUTO, lw=.5,
                alpha=.7, label="Leitura tratada")
        ax.plot(df.data_hora, df[f"{col}_media_movel"], color=COR_SUAVE, lw=.8,
                label="Média móvel (3 h)")
        marcar_fronteira(ax)
        ax.set_ylabel(rot)
        ax.legend(loc="upper right", fontsize=8)
    eixos[0].axhline(LIMIAR_UMIDADE, color="black", ls=":", lw=1)
    eixos[0].set_title("Evolução da umidade e do pH (jan–mar/2026)")
    eixos[1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    eixos[1].set_xlabel("Data simulada (tracejado: fim da coleta Wokwi)")
    fig.tight_layout()
    salvar(fig, pasta, "1_evolucao_umidade_ph.png")


def grafico_zoom(df, pasta):
    """Grafico 2: primeiros 3 dias, onde a media movel fica visivel."""
    z = df[df.data_hora < "2026-01-04"]
    fig, eixos = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True)
    for ax, col, rot in [(eixos[0], "umidade", "Umidade (%)"),
                         (eixos[1], "ph", "pH (escala fictícia)")]:
        ax.step(z.data_hora, z[f"{col}_original"], where="post",
                color=COR_BRUTO, lw=1.5, label="Leitura tratada")
        ax.plot(z.data_hora, z[f"{col}_media_movel"], color=COR_SUAVE, lw=2,
                marker="o", ms=3, label="Média móvel (3 h)")
        marcar_fronteira(ax)
        ax.set_ylabel(rot)
        ax.legend(loc="upper right", fontsize=8)
    eixos[0].set_title("Zoom nos 3 primeiros dias: leitura tratada x média móvel")
    eixos[1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh"))
    eixos[1].set_xlabel("Data simulada (tracejado: fim da coleta Wokwi)")
    fig.tight_layout()
    salvar(fig, pasta, "2_zoom_bruto_vs_suavizado.png")


def grafico_bomba(df, pasta):
    """Grafico 3: umidade x acionamento da bomba (serie + boxplot)."""
    z = df[df.data_hora < "2026-01-04"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    ax1.plot(z.data_hora, z.umidade, color="#34495e", lw=1.2, label="Umidade")
    ax1.axhline(LIMIAR_UMIDADE, color="black", ls=":", label="Limiar de 50%")
    # Sombreia cada hora em que o rele ficou ligado.
    ligadas = z[z.bomba == 1].data_hora
    for i, t in enumerate(ligadas):
        ax1.axvspan(t, t + pd.Timedelta(hours=1), color=COR_BOMBA, alpha=.45,
                    label="Bomba ligada" if i == 0 else None)
    marcar_fronteira(ax1)
    ax1.set_title("Umidade e acionamentos da bomba (3 primeiros dias)")
    ax1.set_ylabel("Umidade (%)")
    ax1.set_xlabel("Data simulada")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh"))
    ax1.legend(loc="upper right", fontsize=8)
    d = df.assign(estado=df.bomba.map({0: "Desligada", 1: "Ligada"}))
    sns.boxplot(data=d, x="estado", y="umidade", hue="estado", ax=ax2,
                order=["Desligada", "Ligada"], hue_order=["Desligada", "Ligada"],
                palette={"Desligada": COR_BRUTO, "Ligada": COR_BOMBA}, legend=False)
    ax2.axhline(LIMIAR_UMIDADE, color="black", ls=":")
    ax2.set_title("Umidade por estado da bomba (90 dias)")
    ax2.set_xlabel("Estado da bomba")
    ax2.set_ylabel("Umidade (%)")
    fig.tight_layout()
    salvar(fig, pasta, "3_umidade_vs_bomba.png")


def grafico_distribuicoes(df, pasta):
    """Grafico 4: distribuicao de cada sensor (S1 umidade, S2 pH, S3 N/P/K)."""
    fig, eixos = plt.subplots(2, 3, figsize=(14, 8))
    sns.histplot(df, x="umidade", bins=40, color="#2e86c1", ax=eixos[0, 0])
    eixos[0, 0].axvline(LIMIAR_UMIDADE, color="black", ls=":")
    eixos[0, 0].set(title="Umidade (S1)", xlabel="Umidade (%)", ylabel="Horas")
    sns.histplot(df, x="ph", bins=40, color="#8e44ad", ax=eixos[0, 1])
    eixos[0, 1].set(title="pH (S2, escala fictícia)", xlabel="pH", ylabel="Horas")
    pct = (df[["nitrogenio", "fosforo", "potassio"]].mean() * 100)
    pct.index = ["N", "P", "K"]
    sns.barplot(x=pct.index, y=pct.values, hue=pct.index, legend=False,
                palette="Greens", ax=eixos[0, 2])
    eixos[0, 2].set(title="Nutrientes (S3): % das horas marcado disponível",
                    xlabel="Nutriente", ylabel="% das horas", ylim=(0, pct.max() * 1.3))
    for i, v in enumerate(pct.values):
        eixos[0, 2].text(i, v + pct.max() * 0.02, f"{v:.1f}%", ha="center", fontsize=9)
    sns.boxplot(data=df, x="origem", y="umidade", hue="origem", legend=False,
                palette="Set2", ax=eixos[1, 0])
    eixos[1, 0].set(title="Umidade por origem", xlabel="", ylabel="Umidade (%)")
    sns.boxplot(data=df, x="origem", y="ph", hue="origem", legend=False,
                palette="Set2", ax=eixos[1, 1])
    eixos[1, 1].set(title="pH por origem", xlabel="", ylabel="pH")
    # Boxplot por origem: mostra se o complemento imita a faixa coletada.
    pct_o = (df.groupby("origem")[["nitrogenio", "fosforo", "potassio"]].mean() * 100)
    pct_o.columns = ["N", "P", "K"]
    pct_o.T.plot.bar(ax=eixos[1, 2], rot=0, color=["#8fb996", "#c9a66b"])
    eixos[1, 2].set(title="Nutrientes por origem", xlabel="Nutriente",
                    ylabel="% das horas disponível")
    eixos[1, 2].legend(title="", fontsize=8)
    fig.suptitle("Distribuição das leituras de cada sensor", fontweight="bold")
    fig.tight_layout()
    salvar(fig, pasta, "4_distribuicoes_sensores.png")


def grafico_agua(df, pasta):
    """Grafico 5: horas de bomba ligada por dia e agua estimada por mes."""
    dia = df.set_index("data_hora").bomba_min.resample("D").sum() / 60
    mes = df.set_index("data_hora").agua_estimada_l.resample("MS").sum()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8),
                                   gridspec_kw={"width_ratios": [2.2, 1]})
    ax1.bar(dia.index, dia.values, color=COR_BOMBA, width=.9)
    ax1.axhline(dia.mean(), color="black", ls="--", lw=1,
                label=f"Média: {dia.mean():.1f} h/dia")
    ax1.set(title="Tempo de bomba ligada por dia", ylabel="Horas ligadas",
            xlabel="Data simulada")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax1.legend(fontsize=8)
    nomes = ["Jan/26", "Fev/26", "Mar/26"][:len(mes)]
    ax2.bar(nomes, mes.values / 1000, color="#2e86c1")
    for i, v in enumerate(mes.values / 1000):
        ax2.text(i, v + .2, f"{v:.1f}", ha="center", fontsize=9)
    ax2.set(title="Água estimada por mês (2 L/min)", ylabel="Milhares de litros")
    fig.suptitle("Indicadores de manejo (predominantemente sintéticos)", fontweight="bold")
    fig.tight_layout()
    salvar(fig, pasta, "5_agua_e_horas_ligadas.png")


def grafico_correlacao(df, pasta):
    """Grafico 6: matriz de correlacao (conjunto completo x so coleta Wokwi).

    'chuva_prevista' fica de fora: e constante (0) e a correlacao seria
    indefinida (NaN), nao zero.
    """
    completo = df[VARIAVEIS].corr()
    wokwi = df.loc[df.simulado == 0, VARIAVEIS].corr()
    fig, eixos = plt.subplots(1, 2, figsize=(15, 6))
    for ax, corr, titulo in [(eixos[0], completo, f"Conjunto completo (n = {len(df)})"),
                             (eixos[1], wokwi, f"Só coleta Wokwi (n = {(df.simulado == 0).sum()})")]:
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
                    square=True, linewidths=.5, ax=ax,
                    xticklabels=[ROTULOS[c] for c in corr.columns],
                    yticklabels=[ROTULOS[c] for c in corr.index])
        ax.set_title(titulo)
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Correlação de Pearson entre sensores e acionamento da bomba",
                 fontweight="bold")
    fig.tight_layout()
    salvar(fig, pasta, "6_correlacao_heatmap.png")
    ranking = pd.DataFrame({"completo": completo["bomba"], "so_wokwi": wokwi["bomba"]})
    ranking = ranking.drop("bomba").round(3)
    ranking = ranking.reindex(ranking.completo.abs().sort_values(ascending=False).index)
    ranking.to_csv(pasta / "correlacao_com_bomba.csv")
    print("\nCorrelação de cada variável com a bomba:\n", ranking)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", default="resultados/leituras_tratadas.csv")
    ap.add_argument("--saida", default="resultados/graficos")
    args = ap.parse_args()
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update({"axes.titleweight": "bold"})
    df = carregar(args.entrada)
    grafico_evolucao(df, pasta)
    grafico_zoom(df, pasta)
    grafico_bomba(df, pasta)
    grafico_distribuicoes(df, pasta)
    grafico_agua(df, pasta)
    grafico_correlacao(df, pasta)


if __name__ == "__main__":
    main()


