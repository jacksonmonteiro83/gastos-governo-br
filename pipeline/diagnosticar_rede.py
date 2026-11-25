"""Diagnóstico de conectividade com o Tesouro Transparente a partir do runner do GitHub.

Testa host com e sem www, IPv4 x IPv6, User-Agent de navegador x padrão do requests, e a página inicial,
para separar "site fora do ar" de "bloqueio ao GitHub" e de "endereço mudou".

    python -m pipeline.diagnosticar_rede
"""
import socket
import subprocess

import requests

ALVOS = [
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show?id=ab56485b-9c40-4efb-8563-9ce3e1973c4b",
    "https://tesourotransparente.gov.br/ckan/api/3/action/package_show?id=ab56485b-9c40-4efb-8563-9ce3e1973c4b",
    "https://www.tesourotransparente.gov.br/",
    "https://www.gov.br/",   # controle: um site .gov.br qualquer
    "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO",  # despesas, cartão e emendas
    "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/last%201",                 # IBGE (população por UF)
    "https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/",           # IBGE (projeções)
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json",  # controle: o BCB funciona
]
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def dns(host: str) -> None:
    for fam, nome in ((socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")):
        try:
            print(f"   DNS {nome}:", sorted({i[4][0] for i in socket.getaddrinfo(host, 443, fam)}))
        except OSError as e:
            print(f"   DNS {nome}: falhou ({e})")


def http(url: str, **kw) -> str:
    try:
        r = requests.get(url, timeout=30, stream=True, **kw)   # stream: não baixa o arquivo inteiro, só o cabeçalho
        return f"HTTP {r.status_code}, {r.headers.get('content-length', '?')} bytes, {r.headers.get('content-type')}"
    except Exception as e:  # noqa: BLE001 - é um diagnóstico, queremos ver qualquer erro
        return f"ERRO {type(e).__name__}: {str(e)[:140]}"


def main() -> None:
    for url in ALVOS:
        host = url.split("/")[2]
        print(f"\n== {url[:95]}")
        dns(host)
        print("   requests padrão  :", http(url))
        print("   UA de navegador  :", http(url, headers=NAVEGADOR))
        for flag in ("-4", "-6"):
            p = subprocess.run(["curl", flag, "-sS", "-o", "/dev/null", "-m", "30", "-w", "%{http_code} %{remote_ip} %{time_total}s",
                                "-A", NAVEGADOR["User-Agent"], url], capture_output=True, text=True)
            print(f"   curl {flag}         :", (p.stdout or p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr).strip() else "sem saída")


if __name__ == "__main__":
    main()
