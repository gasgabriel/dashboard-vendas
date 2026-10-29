"""Linha de comando: python -m pipeline [--intervalo SEGUNDOS]"""
import argparse
import logging
import sys
import time

from .executar import executar
from .extracao import ErroDeExtracao

log = logging.getLogger("pipeline")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pipeline",
                                description="Carrega as vendas no PostgreSQL.")
    p.add_argument("--pasta", default=None, help="pasta com os CSVs (padrão: dados)")
    p.add_argument("--url", default=None, help="URL do CSV da planilha do Google")
    p.add_argument("--intervalo", type=int, default=0,
                   help="repete a cada N segundos (0 = roda uma vez e sai)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.intervalo <= 0:
        try:
            executar(args.pasta, args.url)
        except ErroDeExtracao as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 1
        return 0

    while True:  # modo agendado: uma falha não derruba o serviço
        try:
            executar(args.pasta, args.url)
        except Exception:
            log.exception("A execução falhou; tentando de novo no próximo ciclo")
        log.info("Próxima execução em %s segundos", args.intervalo)
        time.sleep(args.intervalo)