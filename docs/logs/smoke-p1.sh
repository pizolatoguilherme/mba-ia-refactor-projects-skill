#!/usr/bin/env bash
B="$1"; OUT="$2"; : > "$OUT"
req() { local m="$1" p="$2" body="$3" hdr="$4"; local a=(-s -o /tmp/_rb1 -w '%{http_code}' -X "$m")
  [ -n "$body" ] && a+=(-H 'Content-Type: application/json' -d "$body"); [ -n "$hdr" ] && a+=(-H "$hdr")
  local c; c=$(curl "${a[@]}" "$B$p"); printf '%-6s %-32s %-14s -> %s | %s\n' "$m" "$p" "${hdr:+[token]}" "$c" "$(head -c 140 /tmp/_rb1 | tr '\n' ' ')" >> "$OUT"; }
req GET /
req GET /health
req GET /produtos
req GET "/produtos/busca?q=gamer&preco_max=3000"
req GET /produtos/1
req GET /produtos/999
req POST /produtos '{"nome":"Produto Smoke","descricao":"x","preco":10.5,"estoque":5,"categoria":"geral"}'
req POST /produtos '{"nome":"X"}'
req POST /produtos '{"nome":"Ok","preco":-1,"estoque":1}'
req PUT /produtos/11 '{"nome":"Produto Smoke 2","preco":12,"estoque":4,"categoria":"geral"}'
req PUT /produtos/999 '{"nome":"Nada","preco":1,"estoque":1}'
req DELETE /produtos/11
req DELETE /produtos/999
req GET /usuarios
req GET /usuarios/1
req GET /usuarios/999
req POST /usuarios '{"nome":"Smoke","email":"smoke@x.com","senha":"s3nha"}'
req POST /usuarios '{"nome":"Smoke"}'
req POST /login '{"email":"admin@loja.com","senha":"admin123"}'
req POST /login '{"email":"admin@loja.com","senha":"errada"}'
req POST /login '{"email":"x@x.com","senha":"'"'"' OR '"'"'1'"'"'='"'"'1"}'
req POST /pedidos '{"usuario_id":2,"itens":[{"produto_id":2,"quantidade":2},{"produto_id":3,"quantidade":1}]}'
req POST /pedidos '{"usuario_id":2,"itens":[{"produto_id":1,"quantidade":999}]}'
req POST /pedidos '{"usuario_id":2,"itens":[]}'
req GET /pedidos
req GET /pedidos/usuario/2
req PUT /pedidos/1/status '{"status":"aprovado"}'
req PUT /pedidos/1/status '{"status":"invalido"}'
req GET /relatorios/vendas
req POST /admin/query '{"sql":"SELECT COUNT(*) AS n FROM produtos"}'
req POST /admin/query '{"sql":"SELECT COUNT(*) AS n FROM produtos"}' "X-Admin-Token: smoke-token"
req POST /admin/reset-db
req POST /admin/reset-db '' "X-Admin-Token: smoke-token"
req GET /produtos
