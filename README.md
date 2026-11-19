# Gastos do Governo Federal (Brasil)

Para onde vai o dinheiro do governo federal, em valores reais (corrigidos pelo IPCA) e em % do PIB. Dados abertos, pipeline automatizado e três painéis publicados.

**Site:** https://jacksonmonteiro83.github.io/gastos-governo-br/

| Início | Despesas | Previdência (INSS) | Juros | Emendas | Cartão corporativo |
| --- | --- | --- | --- | --- | --- |
| [![Início](docs/img/index.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/) | [![Despesas](docs/img/despesas.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/despesas.html) | [![Previdência](docs/img/previdencia.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/previdencia.html) | [![Juros](docs/img/juros.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/juros.html) | [![Emendas](docs/img/emendas.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/emendas.html) | [![Cartão](docs/img/cartao.png)](https://jacksonmonteiro83.github.io/gastos-governo-br/cartao.html) |

## O que os dados mostram
- **Juros:** R$ 12,81 tri pagos em juros da dívida desde 1997, em valores de hoje, 20,8% de tudo que o governo central gastou. Só em 2025, R$ 933 bi (R$ 2,56 bi por dia), 10,7× o investimento federal.
- **Despesas por função (2025, sem rolagem da dívida):** R$ 3,27 tri em valores de hoje. A previdência social é a maior função, com 32,8%; juros e encargos da dívida, 11,7%; saúde, 7,0%; educação, 5,2%. A rolagem da dívida (amortização e refinanciamento) foi mais R$ 1,87 tri, fora dessas contas. Sem sobreposição, previdência, pessoal e juros somam 52,2% do gasto realizado (R$ 1,71 tri, cerca de R$ 4,7 bi por dia); saúde, educação e assistência ficam com 18,9%, e investimentos com 1,0% (subestimado, ver método).
- **Previdência (INSS/RGPS):** em 2025 a arrecadação líquida cobriu 69,1% dos benefícios; o Tesouro pagou a diferença, R$ 333 bi (2,5% do PIB). Em 1997 a cobertura era de 94%. Desde 2010, já descontada a inflação, os benefícios cresceram 72% e a arrecadação, 43%. A diferença chegou a 3,4% do PIB em 2020 e desde então recuou.
- **Envelhecimento:** a página de Previdência cruza a conta com a projeção de população do IBGE (revisão 2024): idosos de 65+ para cada 100 pessoas de 15 a 64 anos, de 2000 a 2070.
- **Emendas parlamentares:** R$ 49,7 bi empenhados em 2025, em valores de hoje. As transferências especiais (direto a estados e municípios) são 14,8%; as emendas de relator somaram R$ 93,3 bi até 2022 e não aparecem nos dados depois disso, enquanto as de comissão saíram de R$ 0,4 bi (2022) para R$ 11,9 bi (2025). 25,9% do valor de 2025 vem sem estado definido. Por habitante, Roraima recebeu R$ 1.285 em 2025 e São Paulo R$ 72 (18 vezes menos): o total por estado varia cerca de 5 vezes, e a população, 62.
- **Cartão corporativo (jan/2013 a out/2026):** R$ 1,40 bi gastos, em valores de hoje. 48,1% do total está sob sigilo, sem data nem favorecido divulgados (41,4% em 2025). Os saques em espécie são 10,1% do total.

## Stack
- **Python / pandas** para ingestão (APIs e planilhas) e agregação
- **Parquet** como formato intermediário; **DuckDB + dbt (dbt-duckdb)** para a camada analítica: staging, marts (previdência, juros, cartão, despesas, emendas) e testes de dados, incluindo um teste de privacidade do cartão
- **Conferência cruzada:** `pipeline/conferir_dbt.py` compara os marts de previdência, despesas e emendas do dbt (SQL) com os painéis publicados pelo Python (pandas); a conta feita de duas formas tem que bater
- **GitHub Actions** para atualização diária, com commits do bot e testes antes de publicar
- **Painéis estáticos** (GitHub Pages) em `docs/`: HTML + SVG puro, sem dependências, com tooltip, tabela de dados e tema claro/escuro

## Fontes
| Fonte | Uso | Status |
|---|---|---|
| Tesouro Transparente | Resultado do Tesouro Nacional (RTN, desde 1997): juros, previdência, despesas, em valores correntes e em R$ constantes (IPCA) | implementado (`pipeline/tesouro.py`) |
| Banco Central (SGS) | IPCA (433), Selic mensal (4390), PIB 12m (4382); juros nominais 4606/4607 para conferência | implementado (`pipeline/bcb.py`, `pipeline/validar_juros.py`) |
| IBGE | Projeções da População, revisão 2024 (2000 a 2070) | implementado (`pipeline/agregar_demografia.py`) |
| IBGE (SIDRA 6579) | População residente estimada por UF, para o valor de emendas por habitante | implementado (`pipeline/populacao_uf.py`) |
| Portal da Transparência (CGU) | Emendas parlamentares, arquivo único desde 2014 (só o arquivo principal; sem favorecidos) | implementado (`pipeline/emendas.py`, `pipeline/agregar_emendas.py`) |
| Portal da Transparência | Cartão corporativo (CPGF), mensal | implementado (`pipeline/cpgf.py`, `pipeline/agregar_cpgf.py`) |
| Portal da Transparência | Orçamento da despesa por ano (órgão, função, grupo de despesa; orçado, empenhado e realizado), sem favorecidos | implementado (`pipeline/transparencia.py`, `pipeline/agregar_despesas.py`) |

## Estrutura
```
pipeline/     ingestão e agregação (gera Parquet em data/raw e os .js dos painéis)
dbt/          modelos SQL (staging, marts), testes de dados (schema.yml e tests/) e macro de leitura de Parquet
tests/        testes Python (pytest)
docs/         site estático: index (início), despesas, previdencia, juros, emendas, cartao + dados gerados (*_data.js) + img/
.github/      workflows: atualização diária, CPGF, validação dos juros, inspeções
```

## Como rodar
```bash
pip install -r requirements.txt
make ingest                                  # BCB + Tesouro para data/raw
python -m pipeline.agregar                   # docs/data.js (visão geral)
python -m pipeline.agregar_previdencia       # docs/previdencia_data.js
python -m pipeline.agregar_demografia        # docs/demografia_data.js
make test                                    # testes Python
make build                                   # dbt (tudo, exceto cartão, despesas e emendas)
make build-cpgf                              # dbt do cartão (precisa do Parquet do CPGF)
make build-despesas                          # dbt das despesas (precisa do Parquet do orçamento)
make conferir                                # dbt x painel (previdência)
make conferir-despesas                       # dbt x painel (despesas)
make build-emendas                           # dbt das emendas (precisa do Parquet das emendas)
make conferir-emendas                        # dbt x painel (emendas)
```
Para publicar: Settings → Pages → Deploy from a branch → `main` / `/docs`. Para ver local, sirva `docs/` (`python -m http.server`) e abra no navegador.

## Observações de método
- **Juros** = juros nominais do governo central (critério abaixo-da-linha, fonte BCB), com o sinal invertido. É valor líquido. O workflow *Validar juros* compara com as séries do BCB do setor público consolidado: o perímetro é diferente, então os números não são idênticos.
- **Saúde e educação** = só despesas do Executivo sujeitas à programação financeira (linhas 4.4.1.3, 4.4.2.1, 4.4.1.4 e 4.4.2.2 da tabela 1.2-A). Folha de pessoal e Fundeb ficam em outras linhas. Essas séries, e a de investimento, só existem a partir de 2008.
- **Previdência** = arrecadação líquida para o RGPS (linha 1.3) e benefícios previdenciários (linha 4.1) do RTN. Não inclui servidores públicos (regimes próprios) nem o BPC. A "necessidade de financiamento" inclui a previdência rural, o que é parte do debate sobre o que contar como déficit. Os benefícios do RTN incluem precatórios e sentenças, então o total difere um pouco do divulgado pelo Ministério da Previdência. Os percentuais do PIB usam valores correntes e o PIB acumulado de dezembro.
- **Despesas por função** = "orçamento realizado" do Portal da Transparência, em R$ de hoje (IPCA médio do ano). Fica de fora a amortização/refinanciamento da dívida (rolagem de títulos, trilhões por ano) e a reserva de contingência; os juros ficam dentro. O "realizado" é a execução do orçamento do próprio ano e não inclui o pagamento de restos a pagar de anos anteriores, o que subestima sobretudo investimentos. Esta página usa o conceito orçamentário e a página de Juros usa o do Tesouro (caixa), então os totais não coincidem.
- **Demografia** = projeção do IBGE, rotulada como projeção a partir de 2025. O painel não projeta o déficit da previdência.
- **Cartão corporativo:** valores corrigidos pelo IPCA usando o mês do extrato. Privacidade: portadores, pessoas físicas e MEIs não entram na saída, só órgãos e empresas.

## Limitações conhecidas
- O Portal da Transparência limita downloads seguidos: a primeira carga completa do cartão (2013 até hoje) precisou de várias execuções do workflow, que guarda os ZIPs já baixados em cache. As atualizações mensais seguintes são rápidas.
- Emendas: o valor é o empenhado (reservado no ano), não o pago, e os anos recentes ainda estão em execução. Parte do valor vem sem estado definido e fica fora do ranking por estado. O Portal classifica como "relator" valores anteriores a 2020; o painel segue essa classificação sem corrigi-la.
- Ainda não há despesas por favorecido ou por documento (empenho, liquidação, pagamento): são arquivos enormes e com pessoas físicas, e o painel usa o orçamento agregado.

## Atualização
O workflow **Atualizar dados** roda todo dia, baixa as fontes, executa os testes e publica os `*_data.js`. Os workflows **Atualizar CPGF** (dia 5), **Atualizar despesas** (dia 6) e **Atualizar emendas** (dia 7) rodam uma vez por mês, ou manualmente.
