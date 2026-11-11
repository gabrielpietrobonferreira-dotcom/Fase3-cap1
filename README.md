# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# Sistema de Gestão de Perdas na Colheita de Cana-de-Açúcar

# FarmTech Solutions — Fase 3, Capítulo 1

Esta pasta reúne a entrega da atividade “Etapas de uma Máquina Agrícola”: coleta simulada, tratamento e indicadores com Pandas e NumPy, gráficos com Matplotlib e Seaborn e integração com Oracle.

> **Limitação dos dados:** somente 27 das 2.160 leituras vieram da coleta Wokwi. As outras 2.133 foram geradas em Python para demonstrar o processamento. As leituras sintéticas não são medições de uma fazenda e não validam o comportamento agronômico do sistema.

## Integrantes

| Nome completo | RM |
|---|---:|
| Gabriela Abrão Batista Pacheco | 575120 |
| Raila Santos Cruz | 576112 |
| Leonardo Yokoda | 575829 |
| Gabriel Pietrobon Ferreira | 574967 |

## Objetivo e escopo

A atividade transforma leituras simuladas do circuito FarmTech em arquivos analisáveis, calcula indicadores diários e mensais, gera gráficos de comportamento e carrega os resultados em tabelas Oracle. A bomba segue uma regra demonstrativa baseada em umidade e previsão manual de chuva.

O circuito associado está no [projeto Wokwi](https://wokwi.com/projects/477882046949237761). O pacote recebido contém o firmware e as bibliotecas usadas, mas não contém o arquivo diagram.json da montagem.

## Arquivos desta etapa

Os caminhos abaixo são relativos à pasta desta atividade:

- Código Python: src/.
- Firmware e bibliotecas Wokwi: src/wokwi/.
- Script Oracle com criação de tabelas e consultas de gestão: sql/schema_farmtech.sql.
- Dados originais do Monitor Serial e dados de manejo da aplicação anterior: dados/.
- Leituras brutas e tratadas, indicadores, relatório de qualidade e gráficos: resultados/.
- Capturas de execução do Oracle: evidencias/oracle/.
- Exemplo de variáveis de conexão, sem credenciais reais: config/oracle.env.example.

## Dados, campos relevantes e origem

### Leituras de sensores

O arquivo leituras_wokwi_originais.csv contém 27 leituras horárias coletadas no Wokwi e organizadas a partir da saída do Monitor Serial. A coleta vai de 1º de janeiro de 2026, 00h, a 2 de janeiro de 2026, 02h. O arquivo resultados/leituras_brutas.csv contém essas 27 leituras mais 2.133 registros sintéticos, totalizando 2.160 horas entre 1º de janeiro e 1º de abril de 2026, com a data final exclusiva. A coluna simulado distingue as origens: 0 para a coleta Wokwi e 1 para o complemento gerado em Python.

A série sintética é reproduzível com NumPy usando a semente 575120. Ela reamostra blocos de seis horas da coleta, acrescenta ruído didático à umidade e ao pH e recalcula o estado sintético da bomba com a regra do firmware. Isso preserva parte das sequências, mas não cria sazonalidade nem dados realistas de uma lavoura. Os resultados gerais devem ser interpretados como resultados de uma série predominantemente sintética.

| Informação | Significado e limite de interpretação |
|---|---|
| data_hora | Início da hora simulada, no calendário fictício da atividade. |
| umidade | Umidade do ar informada pelo DHT22, usada como indicador didático; não mede umidade do solo. |
| ph | Escala fictícia calculada a partir do LDR; não é medição real de pH. |
| nitrogenio, fosforo, potassio | Estados binários dos botões (0 ou 1), não concentrações nem quantidades de nutrientes. |
| bomba | Estado binário do relé: 1 ligado, 0 desligado. |
| chuva_prevista | Estado binário do comando manual de chuva; todas as linhas fornecidas têm valor 0, então esse cenário não foi avaliado. |
| simulado | Origem da leitura: 0 Wokwi, 1 complemento sintético em Python. |
| umidade_media_movel, ph_media_movel | Médias móveis causais de três horas para visualização; não substituem as leituras usadas pela regra da bomba. |
| bomba_min, agua_estimada_l, acionamento | Minutos estimados com a bomba ligada, volume calculado e transição desligada→ligada. O volume usa uma vazão hipotética de 2 L/min, sem medição física. |

O tratamento converte tipos, valida faixas, remove datas inválidas e duplicatas idênticas, interrompe quando há datas conflitantes e interpola apenas lacunas internas de até duas horas para umidade e pH. Estados desconhecidos não são substituídos por zero. O relatório de qualidade registra as contagens e parâmetros usados.

### Origem das Fases 1 e 2

- **Fase 2 — sensores:** a fonte das leituras entregues é a simulação Wokwi ligada acima e a saída do Monitor Serial preservada em leituras_wokwi_originais.csv. O firmware e as bibliotecas estão em src/wokwi/.
- **Fase 2 — manejo:** manejo.json e manejo.txt são os arquivos de manejo recebidos do grupo. Eles são carregados como registros documentais e não são associados por data às leituras de sensores.
- **Fase 1:** os pacotes enviados não continham um arquivo ou conjunto de dados identificável como fonte da Fase 1. O grupo precisa acrescentar aqui a origem exata e o vínculo com a solução anterior, caso a atividade exija esse material.

As datas dos arquivos de manejo são de novembro de 2026 e ficam fora do período simulado dos sensores (janeiro a março de 2026). Elas documentam a carga de dados e não fazem parte das séries dos gráficos.

## Instalação e configuração do Oracle

A equipe pode usar o banco remoto fornecido pela FIAP ou preparar uma instância local. O SQL Developer é a ferramenta para conectar, criar tabelas e executar consultas.

1. **SQL Developer:** baixe o instalador ou pacote para Windows na [página oficial Oracle](https://www.oracle.com/database/sqldeveloper/). Siga o [guia oficial de instalação](https://docs.oracle.com/en/database/oracle/sql-developer/23.1/rptig/installing-and-starting-sql-developer.html); em geral, descompacte o pacote em uma pasta e abra sqldeveloper.exe. Se usar o servidor da FIAP, utilize os dados de conexão fornecidos pela instituição; não é necessário instalar outro servidor local.
2. **Banco local opcional:** se a turma não fornecer um banco remoto, siga o [guia oficial do Oracle AI Database Free para Windows](https://docs.oracle.com/en/database/oracle/oracle-database/26/xeinw/installing-oracle-database-xe.html). Baixe o pacote Windows, extraia-o e execute setup.exe conforme as instruções e requisitos do guia. A primeira base conectável criada por padrão usa o serviço FREEPDB1; um DSN local típico é localhost:1521/FREEPDB1. O Windows e as permissões do computador precisam atender aos requisitos atuais da Oracle.
3. **Conexão:** no SQL Developer, crie uma conexão Basic e informe host, porta, serviço, usuário e senha do banco. Para um banco local, use os dados exibidos pelo instalador; para a FIAP, use os dados institucionais. Teste e conecte.
4. **Tabelas:** na conexão correta, abra sql/schema_farmtech.sql e execute como script. Faça isso uma vez em um schema vazio. O script cria FT_SENSOR_LEITURAS, FT_BOMBA_HISTORICO e FT_MANEJO_CULTURAS e depois contém cinco consultas de gestão.
5. **Python:** instale Python 3.10 ou superior e as dependências listadas em src/requirements.txt.
6. **Credenciais:** configure ORACLE_USER, ORACLE_PASSWORD e ORACLE_DSN apenas no ambiente local. O arquivo de exemplo mostra os nomes, sem senha real. Não salve um arquivo .env preenchido no GitHub.

## Execução a partir da pasta desta atividade

Instale as dependências:

~~~powershell
python -m pip install -r src/requirements.txt
~~~

Gere ou atualize os CSVs de tratamento e indicadores:

~~~powershell
python src/tratamento_indicadores.py --entrada dados/leituras_wokwi_originais.csv --saida resultados --complementar-ate 2026-04-01
~~~

Gere os seis gráficos e a tabela de correlações:

~~~powershell
python src/graficos_correlacao.py --entrada resultados/leituras_tratadas.csv --saida resultados/graficos
~~~

No PowerShell, configure as variáveis para a sessão atual, usando os valores fornecidos pelo administrador do banco:

~~~powershell
$env:ORACLE_USER = "seu_usuario"
$env:ORACLE_PASSWORD = "sua_senha"
$env:ORACLE_DSN = "host:1521/nome_do_servico"
~~~

Carregue a série e os arquivos de manejo. As credenciais não são argumentos e não devem ser escritas no comando:

~~~powershell
python src/carga_oracle_farmtech.py --csv resultados/leituras_tratadas.csv --json dados/manejo.json --txt dados/manejo.txt
~~~

## Estrutura das tabelas Oracle

| Tabela | Conteúdo |
|---|---|
| FT_SENSOR_LEITURAS | Uma linha por hora, com leituras, estados binários, origem, médias móveis e indicadores derivados. DATA_HORA é única. |
| FT_BOMBA_HISTORICO | Estado da bomba, acionamentos, duração e água estimada, ligado à leitura correspondente. |
| FT_MANEJO_CULTURAS | Conteúdo documental de JSON/TXT em CLOB, identificado pelo nome do arquivo e uma chave de registro. |

A carga usa MERGE e pode ser repetida sem duplicar registros por DATA_HORA e arquivo/chave de manejo. O script Python incluído exige que o CSV tenha datas únicas e válidas, valida as faixas numéricas e usa variáveis de ambiente para conexão.

## Gráficos: legenda e interpretação

### 1. Evolução da umidade e do pH

![Série de umidade e pH](resultados/graficos/1_evolucao_umidade_ph.png)

**Legenda:** leituras tratadas e médias móveis causais de três horas; a linha horizontal marca o limiar de 50% para irrigação e a linha vertical separa a coleta Wokwi do complemento em Python.

**Interpretação:** a umidade apresenta trechos próximos de 60–61% e quedas para cerca de 39–43%. Na série completa, a média é 56,3%, com mínimo de 38,7% e máximo de 63,7%. O pH do sensor fictício apresenta degraus definidos pela pequena amostra e pelo método de complemento; não representa variação natural do solo nem uma medição real.

### 2. Zoom: leitura tratada e média móvel

![Zoom da leitura e suavização](resultados/graficos/2_zoom_bruto_vs_suavizado.png)

**Legenda:** primeiras 72 horas, incluindo a coleta Wokwi; compara leitura tratada e média móvel de três horas.

**Interpretação:** a suavização reduz mudanças abruptas, mas atrasa a resposta em até duas horas nos degraus observados. Ela serve para visualização e não deve substituir a leitura usada pelo firmware para acionar a bomba.

### 3. Umidade e estado da bomba

![Umidade e acionamento da bomba](resultados/graficos/3_umidade_vs_bomba.png)

**Legenda:** umidade e horas com bomba ligada no começo da série, além da distribuição de umidade por estado da bomba.

**Interpretação:** na base entregue, a bomba liga quando a umidade está abaixo de 50%. A separação no histórico completo é esperada, pois a bomba sintética foi calculada com essa mesma regra. Isso confirma a implementação da regra nos dados, não a eficácia de irrigação real.

### 4. Distribuição dos sensores e nutrientes

![Distribuição das leituras](resultados/graficos/4_distribuicoes_sensores.png)

**Legenda:** distribuições de umidade e pH, estados binários de N/P/K e comparação entre as 27 leituras Wokwi e a série completa.

**Interpretação:** umidade e pH se concentram em poucos níveis por causa da curta coleta manual e da reamostragem em blocos. As porcentagens de N/P/K descrevem apenas a frequência de botões marcados como disponíveis. Com 27 leituras originais, as frequências da amostra são instáveis.

### 5. Tempo de bomba e água estimada

![Horas da bomba e água estimada](resultados/graficos/5_agua_e_horas_ligadas.png)

**Legenda:** horas de bomba ligada por dia e volume estimado por mês com vazão hipotética de 2 L/min.

**Interpretação:** o histórico completo soma 445 horas ligadas, 165 transições de acionamento e 53.400 L estimados; apenas a coleta Wokwi soma 6 horas ligadas, 2 acionamentos e 720 L estimados. O volume depende diretamente da vazão assumida e não foi medido fisicamente. A maior parte dessas contas usa dados sintéticos.

### 6. Matriz de correlação

![Mapa de calor de correlação](resultados/graficos/6_correlacao_heatmap.png)

**Legenda:** correlação de Pearson das variáveis com o estado da bomba para o histórico completo e para a amostra Wokwi.

| Variável | Série completa | Só Wokwi |
|---|---:|---:|
| Umidade | -0,97 | -0,97 |
| Fósforo | -0,19 | -0,19 |
| Potássio | -0,16 | -0,15 |
| Nitrogênio | -0,11 | -0,19 |
| pH | +0,04 | +0,07 |

**Interpretação:** a umidade tem a relação mais forte com a bomba porque é a variável usada pela regra do firmware. Os valores de N/P/K e pH são fracos e podem refletir a ordem em que os controles foram alterados na simulação; correlação não prova causalidade. Como chuva_prevista não varia, não é possível avaliar seu efeito.

## Evidências Oracle

As cinco capturas das consultas SQL estão em evidencias/oracle/consulta-*.png. Elas registram volume mensal, série de pH, horas de bomba por dia, umidade por estado da bomba e disponibilidade binária de nutrientes.

As capturas originais foram preservadas integralmente. A imagem do DDL mostra as três tabelas criadas e também avisos ORA-01408 nas tentativas de criar dois índices redundantes; o SQL consolidado remove essas instruções duplicadas.

A imagem carga-tentativas-e-sucesso.png também deve ser mantida: ela documenta a depuração até o sucesso. A tela registra uma tentativa com a variável linhas_json não definida, outra com ORA-00001 por datas já existentes e, ao final, uma carga concluída de 2.160 leituras e 2 registros JSON. Esses erros anteriores fazem parte do histórico do desenvolvimento; não corte nem altere essa captura.

Para documentar também o código consolidado desta pasta, o grupo deve executar carga_oracle_farmtech.py no Oracle e acrescentar uma segunda imagem chamada evidencias/oracle/carga-oracle-final.png. O script atual usa MERGE para permitir reexecução e carrega JSON e TXT, então a quantidade de registros de manejo será diferente dos 2 registros JSON mostrados na captura histórica. A nova imagem deve mostrar a execução final e não pode exibir credenciais.

## Vídeo e entrega no Portal do Aluno

**Vídeo demonstrativo:** [Fase 3 — YouTube não listado (0:50)](https://youtu.be/a6uSe4lSsn4).

O arquivo enviado ao Portal do Aluno deve ser um único TXT contendo somente o link do repositório privado e o link do vídeo não listado. O repositório precisa estar privado e compartilhado com o perfil fiap-tutoria.
## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>





