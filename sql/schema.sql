-- Modelo de dados do painel de vendas.
-- Pode rodar várias vezes: "IF NOT EXISTS" não recria o que já existe.

CREATE TABLE IF NOT EXISTS produtos (
    nome      TEXT PRIMARY KEY,
    categoria TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendas (
    id             BIGSERIAL PRIMARY KEY,
    chave          TEXT NOT NULL UNIQUE,   -- identifica a venda; impede duplicar
    data           DATE NOT NULL,
    produto        TEXT NOT NULL REFERENCES produtos (nome),
    regiao         TEXT NOT NULL,
    vendedor       TEXT NOT NULL,
    quantidade     INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10, 2) NOT NULL CHECK (preco_unitario > 0),
    desconto       NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (desconto BETWEEN 0 AND 100),
    -- o próprio banco calcula a receita, então ela nunca fica inconsistente
    receita        NUMERIC(12, 2) GENERATED ALWAYS AS
                   (round(quantidade * preco_unitario * (1 - desconto / 100), 2)) STORED,
    origem         TEXT NOT NULL,          -- de qual arquivo ou planilha veio
    carregado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas (data);

CREATE TABLE IF NOT EXISTS execucoes (
    id       BIGSERIAL PRIMARY KEY,
    inicio   TIMESTAMPTZ NOT NULL DEFAULT now(),
    fim      TIMESTAMPTZ,
    status   TEXT NOT NULL CHECK (status IN ('rodando', 'ok', 'erro')),
    mensagem TEXT
);

CREATE TABLE IF NOT EXISTS cargas (
    id           BIGSERIAL PRIMARY KEY,
    execucao_id  BIGINT NOT NULL REFERENCES execucoes (id),
    origem       TEXT NOT NULL,
    linhas_lidas INTEGER NOT NULL,
    descartadas  INTEGER NOT NULL,
    usadas       INTEGER NOT NULL,
    inseridas    INTEGER NOT NULL            -- as que ainda não estavam no banco
);