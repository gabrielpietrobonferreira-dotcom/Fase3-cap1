"""
FarmTech Solutions | Fase 3 | Preparação de carga Oracle
Responsabilidade deste arquivo: ler CSV tratado e arquivos JSON/TXT da aplicação,
normalizar os registros e persistir em três tabelas Oracle.

O Integrante 4 deve:
1. criar o schema/usuário e executar schema_farmtech.sql;
2. configurar ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN;
3. validar os formatos reais dos JSON/TXT da Fase 2;
4. executar e testar a carga no ambiente Oracle.

Não contém credenciais. Não compartilhe senha no GitHub.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import oracledb


COLUNAS_CSV = [
    "data_hora", "umidade", "ph", "fosforo", "potassio", "nitrogenio",
    "bomba", "simulado", "chuva_prevista", "umidade_media_movel",
    "ph_media_movel", "duracao_min", "bomba_min", "agua_estimada_l",
    "acionamento",
]

SQL_MERGE_SENSOR = """
MERGE INTO FT_SENSOR_LEITURAS t
USING (
    SELECT :data_hora DATA_HORA FROM dual
) s
ON (t.DATA_HORA = s.DATA_HORA)
WHEN MATCHED THEN UPDATE SET
    t.UMIDADE = :umidade, t.PH = :ph,
    t.FOSFORO = :fosforo, t.POTASSIO = :potassio,
    t.NITROGENIO = :nitrogenio, t.BOMBA = :bomba,
    t.SIMULADO = :simulado, t.CHUVA_PREVISTA = :chuva_prevista,
    t.UMIDADE_MM = :umidade_mm, t.PH_MM = :ph_mm,
    t.DURACAO_MIN = :duracao_min, t.BOMBA_MIN = :bomba_min,
    t.AGUA_ESTIMADA_L = :agua_estimada_l, t.ACIONAMENTO = :acionamento
WHEN NOT MATCHED THEN INSERT (
    DATA_HORA, UMIDADE, PH, FOSFORO, POTASSIO, NITROGENIO,
    BOMBA, SIMULADO, CHUVA_PREVISTA, UMIDADE_MM, PH_MM,
    DURACAO_MIN, BOMBA_MIN, AGUA_ESTIMADA_L, ACIONAMENTO
) VALUES (
    :data_hora, :umidade, :ph, :fosforo, :potassio, :nitrogenio,
    :bomba, :simulado, :chuva_prevista, :umidade_mm, :ph_mm,
    :duracao_min, :bomba_min, :agua_estimada_l, :acionamento
)
"""

SQL_MERGE_BOMBA = """
MERGE INTO FT_BOMBA_HISTORICO t
USING (
    SELECT :data_hora DATA_HORA, :leitura_id LEITURA_ID FROM dual
) s
ON (t.DATA_HORA = s.DATA_HORA)
WHEN MATCHED THEN UPDATE SET
    t.LEITURA_ID = s.LEITURA_ID,
    t.ESTADO_BOMBA = :estado_bomba,
    t.ACIONAMENTO = :acionamento,
    t.DURACAO_MIN = :duracao_min,
    t.BOMBA_MIN = :bomba_min,
    t.AGUA_ESTIMADA_L = :agua_estimada_l
WHEN NOT MATCHED THEN INSERT (
    LEITURA_ID, DATA_HORA, ESTADO_BOMBA, ACIONAMENTO,
    DURACAO_MIN, BOMBA_MIN, AGUA_ESTIMADA_L
) VALUES (
    s.LEITURA_ID, s.DATA_HORA, :estado_bomba, :acionamento,
    :duracao_min, :bomba_min, :agua_estimada_l
)
"""

SQL_MERGE_MANEJO = """
MERGE INTO FT_MANEJO_CULTURAS t
USING (
    SELECT :arquivo_origem ARQUIVO_ORIGEM,
           :chave_registro CHAVE_REGISTRO FROM dual
) s
ON (t.ARQUIVO_ORIGEM = s.ARQUIVO_ORIGEM
    AND t.CHAVE_REGISTRO = s.CHAVE_REGISTRO)
WHEN MATCHED THEN UPDATE SET
    t.TIPO_REGISTRO = :tipo_registro,
    t.DADOS_JSON = :dados_json
WHEN NOT MATCHED THEN INSERT (
    ARQUIVO_ORIGEM, CHAVE_REGISTRO, TIPO_REGISTRO, DADOS_JSON
) VALUES (
    :arquivo_origem, :chave_registro, :tipo_registro, :dados_json
)
"""


def valor_numero(valor):
    """Converte vazio/NaN em None; preserva zero como zero."""
    if valor is None or pd.isna(valor) or str(valor).strip() == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def valor_binario(valor):
    numero = valor_numero(valor)
    if numero is None:
        return None
    inteiro = int(numero)
    if numero not in (Decimal(0), Decimal(1)):
        raise ValueError(f"Valor binário inválido: {valor}")
    return inteiro


def carregar_csv(caminho: Path) -> pd.DataFrame:
    df = pd.read_csv(caminho, encoding="utf-8")
    obrigatorias = {"data_hora", "umidade", "ph", "fosforo", "potassio",
                    "nitrogenio", "bomba", "simulado"}
    faltantes = obrigatorias - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes no CSV: {sorted(faltantes)}")

    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    if df["data_hora"].isna().any():
        raise ValueError("Há datas inválidas em data_hora; corrija o CSV antes da carga.")
    if df["data_hora"].duplicated().any():
        raise ValueError("Há data_hora duplicada no CSV; revise antes da carga.")
    df = df.sort_values("data_hora").reset_index(drop=True)
    return df


def preparar_leituras(df: pd.DataFrame) -> list[dict]:
    registros = []
    for _, row in df.iterrows():
        simulado = valor_binario(row.get("simulado"))
        if simulado is None:
            raise ValueError("A coluna simulado não pode conter valores ausentes.")
        umidade = valor_numero(row.get("umidade"))
        ph = valor_numero(row.get("ph"))
        if umidade is not None and not (0 <= umidade <= 100):
            raise ValueError(f"Umidade fora da faixa em {row['data_hora']}: {umidade}")
        if ph is not None and not (0 <= ph <= 14):
            raise ValueError(f"pH fora da faixa em {row['data_hora']}: {ph}")

        dt = row["data_hora"].to_pydatetime()
        registros.append({
            "data_hora": dt,
            "umidade": umidade,
            "ph": ph,
            "fosforo": valor_binario(row.get("fosforo")),
            "potassio": valor_binario(row.get("potassio")),
            "nitrogenio": valor_binario(row.get("nitrogenio")),
            "bomba": valor_binario(row.get("bomba")),
            "simulado": simulado,
            "chuva_prevista": valor_binario(row.get("chuva_prevista")),
            "umidade_mm": valor_numero(row.get("umidade_media_movel")),
            "ph_mm": valor_numero(row.get("ph_media_movel")),
            "duracao_min": valor_numero(row.get("duracao_min")),
            "bomba_min": valor_numero(row.get("bomba_min")),
            "agua_estimada_l": valor_numero(row.get("agua_estimada_l")),
            "acionamento": valor_binario(row.get("acionamento")),
        })
    return registros


def ler_arquivos_manejo(json_paths: list[Path], txt_paths: list[Path]) -> list[dict]:
    """Armazena JSON como JSON textual e TXT linha a linha, sem presumir esquema."""
    saida = []
    for caminho in json_paths:
        with caminho.open("r", encoding="utf-8") as f:
            conteudo = json.load(f)
        itens = conteudo if isinstance(conteudo, list) else [conteudo]
        for i, item in enumerate(itens, start=1):
            saida.append({
                "arquivo_origem": caminho.name,
                "chave_registro": str(item.get("id", i)) if isinstance(item, dict) else str(i),
                "tipo_registro": str(item.get("tipo", item.get("tipo_registro", "JSON")))[:100]
                    if isinstance(item, dict) else "JSON",
                "dados_json": json.dumps(item, ensure_ascii=False, default=str),
            })

    for caminho in txt_paths:
        with caminho.open("r", encoding="utf-8") as f:
            for numero, linha in enumerate(f, start=1):
                texto = linha.strip()
                if not texto:
                    continue
                payload = {"linha": numero, "conteudo": texto}
                saida.append({
                    "arquivo_origem": caminho.name,
                    "chave_registro": f"linha-{numero}",
                    "tipo_registro": "TXT",
                    "dados_json": json.dumps(payload, ensure_ascii=False),
                })
    return saida


def conectar():
    usuario = os.getenv("ORACLE_USER")
    senha = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    if not all([usuario, senha, dsn]):
        raise RuntimeError(
            "Configure ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN nas variáveis de ambiente."
        )
    return oracledb.connect(user=usuario, password=senha, dsn=dsn)


def persistir(conexao, leituras: list[dict], manejo: list[dict]):
    cursor = conexao.cursor()
    try:
        # MERGE usa DATA_HORA como chave natural: executar novamente não duplica.
        for reg in leituras:
            cursor.execute(SQL_MERGE_SENSOR, reg)

        # Obtém a chave gerada para vincular o evento ao registro da leitura.
        for reg in leituras:
            cursor.execute(
                "SELECT LEITURA_ID FROM FT_SENSOR_LEITURAS WHERE DATA_HORA = :dt",
                dt=reg["data_hora"],
            )
            leitura_id = cursor.fetchone()[0]
            cursor.execute(SQL_MERGE_BOMBA, {
                "data_hora": reg["data_hora"],
                "leitura_id": leitura_id,
                "estado_bomba": reg["bomba"],
                "acionamento": reg["acionamento"],
                "duracao_min": reg["duracao_min"],
                "bomba_min": reg["bomba_min"],
                "agua_estimada_l": reg["agua_estimada_l"],
            })

        for item in manejo:
            cursor.execute(SQL_MERGE_MANEJO, item)

        conexao.commit()
        print(f"Carga concluída: {len(leituras)} leituras e {len(manejo)} registros de manejo.")
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Carga de dados FarmTech no Oracle.")
    parser.add_argument("--csv", default="resultados/leituras_tratadas.csv")
    parser.add_argument("--json", nargs="*", default=[], help="Um ou mais arquivos JSON da Fase 2.")
    parser.add_argument("--txt", nargs="*", default=[], help="Um ou mais arquivos TXT da Fase 2.")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")

    df = carregar_csv(csv_path)
    leituras = preparar_leituras(df)
    json_paths = [Path(p) for p in args.json]
    txt_paths = [Path(p) for p in args.txt]
    for p in json_paths + txt_paths:
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {p}")
    manejo = ler_arquivos_manejo(json_paths, txt_paths)

    with conectar() as conexao:
        persistir(conexao, leituras, manejo)


if __name__ == "__main__":
    main()



