-- As consultas do painel, sem filtros, para rodar direto no psql ou no DBeaver.

-- 1. Números principais
SELECT SUM(receita)    AS receita_total,
       COUNT(*)        AS vendas,
       SUM(quantidade) AS itens,
       ROUND(AVG(receita), 2) AS ticket_medio
FROM vendas;

-- 2. Receita por mês, com variação (LAG) e acumulado (SUM OVER)
SELECT to_char(date_trunc('month', data), 'YYYY-MM') AS mes,
       SUM(receita) AS receita,
       SUM(receita) - LAG(SUM(receita)) OVER (ORDER BY date_trunc('month', data)) AS variacao,
       SUM(SUM(receita)) OVER (ORDER BY date_trunc('month', data)) AS acumulado
FROM vendas
GROUP BY date_trunc('month', data)
ORDER BY date_trunc('month', data);

-- 3. Produtos com maior receita (JOIN com a categoria)
SELECT v.produto, p.categoria, SUM(v.receita) AS receita
FROM vendas v
JOIN produtos p ON p.nome = v.produto
GROUP BY v.produto, p.categoria
ORDER BY receita DESC;

-- 4. Receita por categoria
SELECT p.categoria, SUM(v.receita) AS receita
FROM vendas v
JOIN produtos p ON p.nome = v.produto
GROUP BY p.categoria
ORDER BY receita DESC;

-- 5. Ranking de vendedores dentro de cada região (RANK + PARTITION BY)
SELECT regiao, vendedor, SUM(receita) AS receita,
       RANK() OVER (PARTITION BY regiao ORDER BY SUM(receita) DESC) AS posicao
FROM vendas
GROUP BY regiao, vendedor
ORDER BY regiao, posicao;

-- 6. Quantas vendas vieram de cada fonte
SELECT origem, COUNT(*) AS vendas
FROM vendas
GROUP BY origem
ORDER BY origem;