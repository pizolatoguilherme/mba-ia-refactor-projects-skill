#!/usr/bin/env bash
B="$1"; OUT="$2"; : > "$OUT"
req() { local m="$1" p="$2" body="$3"
  local a=(-s -o /tmp/_rb3 -w '%{http_code}' -X "$m")
  [ -n "$body" ] && a+=(-H 'Content-Type: application/json' -d "$body")
  local c; c=$(curl "${a[@]}" "$B$p"); printf '%-6s %-34s -> %s | %s\n' "$m" "$p" "$c" "$(head -c 160 /tmp/_rb3 | tr '\n' ' ')" >> "$OUT"; }
req GET /
req GET /health
req GET /tasks
req GET /tasks/1
req GET /tasks/999
req GET "/tasks/search?q=API&status=pending"
req GET /tasks/stats
req POST /tasks '{"title":"Task smoke","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2030-01-31","tags":["a","b"]}'
req POST /tasks '{"title":"ab"}'
req POST /tasks '{"title":"Status ruim","status":"xpto"}'
req POST /tasks '{"title":"Prioridade texto","priority":"3"}'
req POST /tasks '{"title":"User inexistente","user_id":999}'
req PUT /tasks/11 '{"status":"done","priority":1}'
req PUT /tasks/999 '{"status":"done"}'
req DELETE /tasks/11
req DELETE /tasks/999
req GET /users
req GET /users/1
req GET /users/999
req GET /users/1/tasks
req POST /users '{"name":"Smoke","email":"smoke@email.com","password":"segredo1"}'
req POST /users '{"name":"Dup","email":"smoke@email.com","password":"segredo1"}'
req POST /users '{"name":"Bad","email":"invalido","password":"segredo1"}'
req POST /users '{"name":"Esperto","email":"esperto@email.com","password":"segredo1","role":"admin"}'
req PUT /users/4 '{"name":"Smoke 2"}'
req DELETE /users/4
req POST /login '{"email":"joao@email.com","password":"1234"}'
req POST /login '{"email":"joao@email.com","password":"errada"}'
req POST /login '{}'
req GET /reports/summary
req GET /reports/user/1
req GET /reports/user/999
req GET /categories
req POST /categories '{"name":"Smoke","color":"#123456"}'
req PUT /categories/5 '{"name":"Smoke 2"}'
req DELETE /categories/5
req DELETE /categories/999
