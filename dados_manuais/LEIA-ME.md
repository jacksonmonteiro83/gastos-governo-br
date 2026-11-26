# Arquivo manual do Tesouro

O site do Tesouro Transparente (gov.br) às vezes recusa conexões vindas dos servidores do GitHub.
Quando isso acontece, o pipeline usa o arquivo `tesouro_serie_historica.xlsx` desta pasta.

Para atualizar (uma vez por mês, quando o Tesouro publicar o resultado novo):

1. Abra a página do recurso no navegador, no Brasil:
   https://www.tesourotransparente.gov.br/ckan/dataset/ab56485b-9c40-4efb-8563-9ce3e1973c4b/resource/527ccdb1-3059-42f3-bf23-b5e3ab4c6dc6
   ("Série Histórica - Mensal", XLSX) e baixe o arquivo (o nome muda todo mês, ex.: `seriehistoricajul26.xlsx`).
2. Renomeie para `tesouro_serie_historica.xlsx`.
3. No GitHub: esta pasta > Add file > Upload files > envie o arquivo > Commit changes.
4. Rode o workflow **Atualizar dados**.
