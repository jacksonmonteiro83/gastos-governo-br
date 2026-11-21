"""GET com retentativas para fontes públicas instáveis (BCB, Tesouro, Portal, IBGE)."""
import time

import requests

TENTATIVAS = 5
PAUSA_BASE = 5.0  # segundos; dobra a cada falha (5, 10, 20, 40)
_TRANSITORIOS = {429, 500, 502, 503, 504}


def get_com_retentativas(url: str, params: dict | None = None, timeout: int = 60, tentativas: int = TENTATIVAS, pausa_base: float = PAUSA_BASE,
                         get=requests.get, dormir=time.sleep) -> requests.Response:
    """GET que tenta de novo em erro transitório do servidor (5xx, 429) ou de rede. 4xx de verdade não repete."""
    for n in range(1, tentativas + 1):
        try:
            r = get(url, params=params, timeout=timeout)
            if r.status_code not in _TRANSITORIOS:
                r.raise_for_status()
                return r
            erro = f"HTTP {r.status_code}"
        except (requests.ConnectionError, requests.Timeout) as e:
            erro = type(e).__name__
        if n == tentativas:
            raise RuntimeError(f"Download falhou {tentativas} vezes seguidas ({erro}): {url} {params}")
        espera = pausa_base * 2 ** (n - 1)
        print(f"  {erro}; tentativa {n}/{tentativas}, nova em {espera:.0f}s")
        dormir(espera)
