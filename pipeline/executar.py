"""Orquestra uma execução: extrair, limpar, carregar e registrar o que aconteceu."""
import logging

from . import config
from .carga import conectar, criar_tabelas, inserir_vendas
from .extracao import extrair
from .limpeza import limpar

log = logging.getLogger(__name__)


def _iniciar(conn) -> int:
    cur = conn.execute("INSERT INTO execucoes (status) VALUES ('rodando') RETURNING id")
    exec_id = cur.fetchone()[0]
    conn.commit()  # a execução fica registrada mesmo se a carga falhar depois
    return exec_id


def _finalizar(conn, exec_id: int, status: str, mensagem=None) -> None:
    conn.execute("UPDATE execucoes SET fim = now(), status = %s, mensagem = %s WHERE id = %s",
                 (status, mensagem, exec_id))
    conn.commit()


def executar(pasta=None, url=None, conn=None, **opcoes_http) -> dict:
    """Roda o pipeline inteiro. Se der erro, nada fica pela metade (rollback)."""
    pasta = pasta if pasta is not None else config.pasta_dados()
    url = url if url is not None else config.url_planilha()
    fechar = conn is None
    conn = conn or conectar()
    try:
        criar_tabelas(conn)
        exec_id = _iniciar(conn)
        cargas = []
        try:
            for origem, bruto in extrair(pasta, url, **opcoes_http):
                limpo, resumo = limpar(bruto)
                inseridas = inserir_vendas(conn, limpo, origem)
                conn.execute(
                    "INSERT INTO cargas (execucao_id, origem, linhas_lidas, descartadas, "
                    "usadas, inseridas) VALUES (%s, %s, %s, %s, %s, %s)",
                    (exec_id, origem, resumo.linhas_lidas, resumo.descartadas,
                     resumo.linhas_usadas, inseridas))
                cargas.append({"origem": origem, "lidas": resumo.linhas_lidas,
                               "descartadas": resumo.descartadas,
                               "usadas": resumo.linhas_usadas, "inseridas": inseridas})
                log.info("%s: %s lidas, %s descartadas, %s inseridas",
                         origem, resumo.linhas_lidas, resumo.descartadas, inseridas)
            conn.commit()
            _finalizar(conn, exec_id, "ok")
        except Exception as erro:
            conn.rollback()
            _finalizar(conn, exec_id, "erro", str(erro))
            raise
        return {"execucao_id": exec_id, "cargas": cargas}
    finally:
        if fechar:
            conn.close()