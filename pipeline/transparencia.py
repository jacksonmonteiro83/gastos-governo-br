"""Portal da Transparência: download das despesas (empenho, liquidação, pagamento).

TODO: confirmar na página https://portaldatransparencia.gov.br/download-de-dados/despesas
o padrão atual da URL de download (por período) e os dicionários de dados.
Os arquivos vêm em CSV (AAAAMMDD_Despesas_Pagamento.csv etc.), em ZIP.
Plano: baixar por mês, converter para Parquet particionado por ano/mês em data/raw.
"""


def main() -> None:
    raise NotImplementedError("Implementar após confirmar o padrão de URL do portal.")


if __name__ == "__main__":
    main()
