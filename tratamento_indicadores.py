"""FarmTech - Pessoa A: limpeza, complemento opcional e indicadores.
Execute com --help. Sensores e horas sao simulacoes didaticas.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

SENSORES = ['umidade', 'ph']
BINARIOS = ['fosforo', 'potassio', 'bomba', 'simulado',
            'nitrogenio', 'chuva_prevista']
COLUNAS = ['data_hora', 'umidade', 'ph', 'fosforo', 'potassio',
           'bomba', 'simulado', 'nitrogenio', 'chuva_prevista']


def limpar(arquivo):
    """Mantem a cronologia e flags; nunca imputa o estado da bomba."""
    df = pd.read_csv(arquivo)
    faltantes = set(COLUNAS) - set(df.columns)
    if faltantes:
        raise ValueError(f'Colunas obrigatorias ausentes: {sorted(faltantes)}')
    df = df[COLUNAS].copy()
    auditoria = {'linhas_entrada': len(df)}
    df['data_hora'] = pd.to_datetime(df['data_hora'], errors='coerce',
                                   format='%Y-%m-%d %H:%M:%S')
    auditoria['datas_invalidas_removidas'] = int(df.data_hora.isna().sum())
    df = df.dropna(subset=['data_hora'])
    # Duplicatas identicas sao removidas; estados conflitantes exigem revisao.
    antes = len(df)
    df = df.drop_duplicates()
    auditoria['duplicatas_identicas_removidas'] = antes - len(df)
    if df.data_hora.duplicated().any():
        raise ValueError('Datas repetidas com valores diferentes: revise a origem.')
    df = df.sort_values('data_hora').reset_index(drop=True)
    if df.empty:
        raise ValueError('Nenhuma data valida.')
    if not df.data_hora.eq(df.data_hora.dt.floor('h')).all():
        raise ValueError('Este projeto exige leituras em horas inteiras simuladas.')
    for col in SENSORES + BINARIOS:
        # Infinitos e textos nao numericos viram ausentes.
        df[col] = pd.to_numeric(df[col], errors='coerce').replace(
            [np.inf, -np.inf], np.nan)
        if col in SENSORES:
            superior = 100 if col == 'umidade' else 14
            valido = df[col].between(0, superior)
        else:
            valido = df[col].isin([0, 1])
        df.loc[~valido, col] = np.nan
        auditoria[f'{col}_ausentes_ou_invalidos'] = int(df[col].isna().sum())
    # Origem desconhecida nao pode ser classificada como Wokwi ou sintetica.
    if df.simulado.isna().any():
        raise ValueError('Corrija a coluna simulado: apenas 0 ou 1.')
    for col in SENSORES:
        df[f'{col}_original'] = df[col]
        # Interpola apenas lacunas internas de ate duas HORAS. Reindexar impede
        # interpolar entre leituras separadas por grandes falhas de coleta.
        serie = df.set_index('data_hora')[col].asfreq('h')
        grupos = serie.notna().cumsum()
        tamanho = serie.isna().groupby(grupos).transform('sum')
        candidato = serie.interpolate(method='time', limit_area='inside')
        serie = serie.where(serie.notna() | tamanho.gt(2), candidato)
        df[col] = serie.reindex(df.data_hora).to_numpy()
        df[f'{col}_imputado'] = (df[f'{col}_original'].isna()
                                      & df[col].notna()).astype('int8')
    return df, auditoria


def complementar(df, fim, seed):
    """Reamostra blocos de ate 6 horas da amostra, com ruido pequeno.

    Nao e modelo agronomico nem historico observado. Preserva as linhas
    coletadas e gera somente depois da ultima, ate a data final exclusiva.
    """
    fim = pd.Timestamp(fim)
    if fim != fim.floor('h'):
        raise ValueError('Fim deve ser uma hora inteira.')
    inicio = df.data_hora.max() + pd.Timedelta(hours=1)
    datas = pd.date_range(inicio, fim, freq='h', inclusive='left')
    if not len(datas):
        return df[COLUNAS].copy()
    base = df.loc[df.simulado.eq(0)].dropna(subset=COLUNAS)
    if len(base) < 12:
        raise ValueError('Complemento exige pelo menos 12 linhas Wokwi completas.')
    # Escolhe somente blocos consecutivos, para nao atravessar falhas temporais.
    tamanho = min(6, len(base))
    candidatos = [i for i in range(len(base)-tamanho+1)
                  if base.data_hora.iloc[i+tamanho-1]-base.data_hora.iloc[i]
                  == pd.Timedelta(hours=tamanho-1)]
    if not candidatos:
        raise ValueError('Nao ha bloco consecutivo suficiente para reamostrar.')
    rng = np.random.default_rng(seed)
    blocos = [base.iloc[i:i+tamanho][COLUNAS]
              for i in rng.choice(candidatos,
                                  size=int(np.ceil(len(datas)/tamanho)))]
    novo = pd.concat(blocos, ignore_index=True).iloc[:len(datas)].copy()
    novo['data_hora'] = datas
    for col, desvio, teto in [('umidade', .8, 100), ('ph', .08, 14)]:
        novo[col] = np.round(np.clip(novo[col].to_numpy()
                             + rng.normal(0, desvio, len(novo)), 0, teto), 2)
    novo['simulado'] = 1
    # Nao reamostra bomba independentemente: aplica exatamente a logica enviada.
    novo['bomba'] = ((novo.umidade < 50) & novo.chuva_prevista.eq(0)).astype(int)
    return pd.concat([df[COLUNAS], novo], ignore_index=True)


def processar(df, vazao, janela):
    """Media movel causal; indicadores usam leituras tratadas nao suavizadas."""
    df = df.copy()
    for col in SENSORES:
        # Janela temporal, sem preencher lacunas longas. Exige ao menos 1 leitura.
        serie = df.set_index('data_hora')[col]
        df[f'{col}_media_movel'] = serie.rolling(
            f'{janela}h', min_periods=1, closed='right').mean().to_numpy()
    # Cada linha do firmware descreve a hora seguinte. Uma falha de registro
    # NAO prolonga o ultimo estado por todo o intervalo sem observacoes.
    df['duracao_min'] = 60.0
    df['bomba_min'] = df.bomba * df.duracao_min
    df['agua_estimada_l'] = df.bomba_min * vazao
    anterior = df.bomba.shift()
    consecutivo = df.data_hora.diff().eq(pd.Timedelta(hours=1))
    # Firmware inicia desligado; conta a primeira ligacao se a origem e preservada.
    acionamento = pd.Series(np.nan, index=df.index)
    conhecidos = consecutivo & anterior.notna() & df.bomba.notna()
    acionamento.loc[conhecidos] = ((anterior.eq(0)) & df.bomba.eq(1))[conhecidos].astype(int)
    # Inicio do calendario do firmware e o unico estado inicial conhecido.
    if df.data_hora.iloc[0] == pd.Timestamp('2026-01-01 00:00:00'):
        acionamento.iloc[0] = df.bomba.iloc[0]
    df['acionamento'] = acionamento
    return df


def indicadores(df, frequencia):
    """Somatorios desconhecidos ficam vazios; contagens conhecidas sao explicitas."""
    grupos = df.groupby(pd.Grouper(key='data_hora', freq=frequencia))
    saida = grupos.agg(
        leituras=('data_hora', 'size'),
        leituras_wokwi=('simulado', lambda s: int(s.eq(0).sum())),
        leituras_python=('simulado', lambda s: int(s.eq(1).sum())),
        horas_bomba_conhecida=('bomba', 'count'),
        bomba_ligada_min=('bomba_min', lambda s: s.sum(min_count=1)),
        agua_estimada_l=('agua_estimada_l', lambda s: s.sum(min_count=1)),
        acionamentos_conhecidos=('acionamento', lambda s: s.sum(min_count=1)),
        transicoes_desconhecidas=('acionamento', lambda s: int(s.isna().sum())),
        umidade_media=('umidade', 'mean'), umidade_min=('umidade', 'min'),
        umidade_max=('umidade', 'max'), umidade_validas=('umidade', 'count'),
        ph_medio=('ph', 'mean'), ph_min=('ph', 'min'), ph_max=('ph', 'max'),
        ph_validos=('ph', 'count'))
    saida['bomba_ligada_h'] = saida.bomba_ligada_min / 60
    saida['horas_sem_registro'] = [
        max(0, int(((t + pd.tseries.frequencies.to_offset(frequencia))-t)
                   / pd.Timedelta(hours=1)) - n)
        for t, n in zip(saida.index, saida.leituras)]
    return saida.reset_index().rename(columns={'data_hora': 'periodo'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', default='dados/leituras_wokwi_originais.csv')
    parser.add_argument('--saida', default='resultados')
    parser.add_argument('--complementar-ate', help='Data final EXCLUSIVA, ex.: 2026-04-01')
    parser.add_argument('--vazao', type=float, default=2.0, help='L/min, hipotese didatica')
    parser.add_argument('--janela', type=int, default=3, help='Horas da media movel')
    parser.add_argument('--seed', type=int, default=575120)
    args = parser.parse_args()
    if not np.isfinite(args.vazao) or args.vazao <= 0 or args.janela < 1:
        parser.error('Vazao deve ser positiva e finita; janela deve ser >= 1.')
    out = Path(args.saida)
    out.mkdir(parents=True, exist_ok=True)
    df, auditoria = limpar(args.entrada)
    # Bruto expandido preserva as leituras de entrada, inclusive invalidas;
    # a base limpa e usada somente para aprender o padrao do complemento.
    bruto = pd.read_csv(args.entrada)[COLUNAS]
    if args.complementar_ate:
        expandido = complementar(df, args.complementar_ate, args.seed)
        extras = expandido.loc[expandido.simulado.eq(1)
                                & (expandido.data_hora > df.data_hora.max())]
        bruto = pd.concat([bruto, extras], ignore_index=True)
    bruto.to_csv(out/'leituras_brutas.csv', index=False)
    # Roda a mesma limpeza no conjunto completo antes de calcular indicadores.
    tratado, auditoria_total = limpar(out/'leituras_brutas.csv')
    tratado = processar(tratado, args.vazao, args.janela)
    tratado.to_csv(out/'leituras_tratadas.csv', index=False, float_format='%.6f')
    indicadores(tratado, 'D').to_csv(out/'indicadores_diarios.csv', index=False,
                                    float_format='%.6f')
    indicadores(tratado, 'MS').to_csv(out/'indicadores_mensais.csv', index=False,
                                     float_format='%.6f')
    resumo = {'entrada': auditoria, 'conjunto_completo': auditoria_total,
              'linhas_wokwi': int(tratado.simulado.eq(0).sum()),
              'linhas_python': int(tratado.simulado.eq(1).sum()),
              'primeira_hora': str(tratado.data_hora.min()),
              'fim_cobertura_exclusivo': str(tratado.data_hora.max()+pd.Timedelta(hours=1)),
              'vazao_l_min': args.vazao, 'janela_horas': args.janela,
              'semente': args.seed, 'bomba_ligada_h': float(tratado.bomba_min.sum()/60),
              'agua_estimada_l': float(tratado.agua_estimada_l.sum()),
              'acionamentos_conhecidos': int(tratado.acionamento.sum())}
    (out/'relatorio_qualidade.json').write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()


