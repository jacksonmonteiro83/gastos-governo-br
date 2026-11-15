# Gastos do Governo Federal (Brasil)

Projeto de dados abertos: para onde vai o dinheiro do governo federal, em valores reais (corrigidos pelo IPCA) e em % do PIB.

## Stack
- **Python** para ingestão (APIs e CSVs)
- **DuckDB + Parquet** para armazenamento e consultas
- **dbt (dbt-duckdb)** para transformações em camadas (staging → marts) com testes
- **GitHub Actions** para atualização diária
- **Dashboard estático** (GitHub Pages) em `docs/`

## Fontes
| Fonte | Uso | Status |
|---|---|---|
| Banco Central (SGS) | IPCA (433), Selic mensal (4390), PIB 12m (4382) | implementado |
| Portal da Transparência | Despesas (empenho, liquidação, pagamento) | a implementar (`pipeline/transparencia.py`) |
| Tesouro Transparente | Resultado do Tesouro Nacional (desde 1997) | implementado (`pipeline/tesouro.py`): 11 abas mensais em formato longo, valores correntes e em R$ de jul/2026 (IPCA) |

## Estrutura
```
pipeline/     ingestão (gera Parquet em data/raw)
dbt/          modelos SQL (staging e marts) e testes
tests/        testes Python
docs/         dashboard estático (index.html + data.js gerado por pipeline/agregar.py)
.github/      workflow de atualização diária
```

## Como rodar
```bash
pip install -r requirements.txt
make ingest   # baixa as séries do BCB para data/raw
make build    # roda dbt (modelos e testes)
make test     # testes Python
```

## Perguntas que o projeto responde
- Quanto o governo gastou com juros desde 1997, em valores de hoje?
- Juros vs. saúde, educação e investimento, ano a ano.
- Quanto custa por dia o governo federal?
- Quais gastos fogem do padrão (detecção de anomalias)?

## Dashboard
`docs/index.html` lê `docs/data.js` (gerado por `python -m pipeline.agregar`) e desenha dois gráficos em SVG puro, sem dependências: juros contra saúde, educação e investimento, e a composição do gasto total por ano. Para publicar: Settings → Pages → Deploy from a branch → `main` / `/docs`. Para ver local: abra `docs/index.html` no navegador.

## Observações de método
- Juros = juros nominais do governo central (critério abaixo-da-linha, fonte BCB), com o sinal invertido. É valor líquido, não o bruto do orçamento.
- Saúde e educação = só despesas do Executivo sujeitas à programação financeira (linhas 4.4.1.3, 4.4.2.1, 4.4.1.4, 4.4.2.2 da tabela 1.2-A). Folha de pessoal e Fundeb ficam em outras linhas.
- Saúde, educação e investimento só existem na série a partir de 2008; antes disso a fonte traz zeros, que viram nulos.
