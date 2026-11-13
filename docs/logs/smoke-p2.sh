#!/usr/bin/env bash
B="$1"; OUT="$2"; : > "$OUT"
req() { local m="$1" p="$2" body="$3" hdr="$4"; local a=(-s -o /tmp/_rb2 -w '%{http_code}' -X "$m")
  [ -n "$body" ] && a+=(-H 'Content-Type: application/json' -d "$body"); [ -n "$hdr" ] && a+=(-H "$hdr")
  local c; c=$(curl "${a[@]}" "$B$p"); printf '%-6s %-28s %-8s -> %s | %s\n' "$m" "$p" "${hdr:+[token]}" "$c" "$(head -c 300 /tmp/_rb2 | tr '\n' ' ')" >> "$OUT"; }
req GET  /api/admin/financial-report
req GET  /api/admin/financial-report "" "X-Admin-Token: smoke-token"
req POST /api/checkout '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
req POST /api/checkout '{"usr":"João","eml":"joao@teste.com","pwd":"123","c_id":1,"card":"5111222233334444"}'
req POST /api/checkout '{"usr":"Leonan","eml":"leonan@fullcycle.com.br","pwd":"x","c_id":2,"card":"4000000000000000"}'
req POST /api/checkout '{"usr":"Sem curso","eml":"a@b.com","pwd":"x","c_id":99,"card":"4111"}'
req POST /api/checkout '{"usr":"Faltando"}'
req GET  /api/admin/financial-report
req GET  /api/admin/financial-report "" "X-Admin-Token: smoke-token"
req DELETE /api/users/1
req DELETE /api/users/1 "" "X-Admin-Token: smoke-token"
req GET  /api/admin/financial-report
req GET  /api/admin/financial-report "" "X-Admin-Token: smoke-token"
