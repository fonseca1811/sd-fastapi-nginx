# API de Registros com FastAPI + Nginx (proxy reverso)

Atividade complementar de **Sistemas Distribuídos**: continuação do projeto da aula anterior.

**Integrantes**
- João Vitor Fonseca Matos
- (nome do integrante 2)
- (nome do integrante 3)

O que foi feito nesta etapa:

1. **Código separado em pacotes por responsabilidade:** rotas, contratos de dados, acesso ao banco e infraestrutura.
2. **Nginx na frente da aplicação:** funciona como proxy reverso e faz o rate limiting, os cabeçalhos de segurança e as respostas de erro padronizadas. O Uvicorn fica isolado em `127.0.0.1:8000`.

---

## 1. Estrutura do projeto

```
sd-fastapi-nginx/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada, middlewares e registro de rotas
│   ├── core/
│   │   ├── __init__.py
│   │   └── database.py          # Conexão SQLite e inicialização do banco
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── registro.py          # Modelos Pydantic (validação de dados)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── registro.py          # Padrão Repository (CRUD e SQL isolado)
│   └── api/
│       ├── __init__.py          # Junta os routers (controladores modulares)
│       └── routes/
│           ├── __init__.py
│           └── registros.py     # Endpoints /registros (@router)
├── nginx/
│   └── fastapi.conf             # Configuração do Nginx (proxy reverso)
├── scripts/
│   └── teste_rate_limit.py      # Script para testar o rate limiting
├── pyproject.toml
├── requirements.txt
└── README.md
```

Cada camada só conversa com a camada vizinha:

```
Rota (api/routes)  →  Repository (repositories)  →  Banco (core/database)
        ↑                                    
   Schemas (validam entrada e saída)
```

### Endpoints

| Método | Rota               | Descrição                                   |
|--------|--------------------|---------------------------------------------|
| GET    | `/`                | Mensagem de status                          |
| GET    | `/health`          | Health check da API                         |
| GET    | `/info`            | Mostra se a requisição passou pelo Nginx    |
| GET    | `/registros`       | Lista registros (`?limite=` e `?offset=`)   |
| GET    | `/registros/{id}`  | Busca um registro                           |
| POST   | `/registros`       | Cria um registro                            |
| PUT    | `/registros/{id}`  | Atualiza um registro                        |
| DELETE | `/registros/{id}`  | Remove um registro                          |

---

## 2. Rodando a API

Com **uv** (recomendado):

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1"
```

Ou com **pip**:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate   |   Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1"
```

> `--host 127.0.0.1` faz o Uvicorn aceitar conexões **só da própria máquina**, então ninguém de fora acessa a porta 8000.
> `--proxy-headers` e `--forwarded-allow-ips` fazem o Uvicorn confiar nos cabeçalhos `X-Forwarded-*` enviados pelo Nginx. Assim, a API enxerga o IP real do cliente.

---

## 3. Mini tutorial: configurando o Nginx

### 3.1 O que o Nginx faz aqui

O Nginx é um servidor web de alto desempenho. Neste projeto ele funciona como **proxy reverso**: é a porta de entrada do sistema. O cliente conversa só com o Nginx (porta **8080**), e o Nginx repassa a requisição para o Uvicorn (porta 8000), que fica escondido.

```
                 porta 8080                         127.0.0.1:8000
 ┌─────────┐   ┌──────────────────────────┐       ┌──────────────────┐     ┌────────┐
 │ Cliente │──▶│          NGINX           │──────▶│ Uvicorn + FastAPI│────▶│ SQLite │
 │(browser)│◀──│ rate limit · segurança · │◀──────│   (app.main:app) │◀────│        │
 └─────────┘   │ gzip · erros padronizados│       └──────────────────┘     └────────┘
               └──────────────────────────┘
```

Vantagens:
- **Isolamento:** a porta interna da aplicação não fica exposta.
- **Segurança:** o tráfego abusivo é barrado (rate limiting) antes de consumir recursos do Python.
- **Desempenho:** o Nginx atende milhares de conexões de forma assíncrona e só repassa ao Uvicorn o que precisa de processamento.
- **Escalabilidade:** o mesmo Nginx pode distribuir a carga entre várias instâncias da API (veja o bônus na seção 3.6).

### 3.2 Instalação

**Linux (Ubuntu/Debian) ou WSL**

```bash
sudo apt update
sudo apt install nginx -y
nginx -v
```

**Windows**

1. Baixe a versão *Stable* (zip) em <https://nginx.org/en/download.html>.
2. Extraia para `C:\nginx`.
3. Os comandos são executados dentro dessa pasta (PowerShell ou CMD).

**macOS**

```bash
brew install nginx
```

### 3.3 Configuração

Toda a configuração está em [`nginx/fastapi.conf`](nginx/fastapi.conf). Copie esse arquivo para o local certo do seu sistema:

| Sistema         | Onde colocar                                   | Passo extra                                                               |
|-----------------|------------------------------------------------|---------------------------------------------------------------------------|
| Linux / WSL     | `/etc/nginx/conf.d/fastapi.conf`               | Nenhum (o `nginx.conf` já inclui a pasta `conf.d`)                         |
| Windows         | `C:\nginx\conf\fastapi.conf`                   | Adicionar `include fastapi.conf;` dentro do bloco `http { }` de `conf\nginx.conf` |
| macOS (Homebrew)| `/opt/homebrew/etc/nginx/servers/fastapi.conf` | Nenhum                                                                    |

Linux / WSL:

```bash
sudo cp nginx/fastapi.conf /etc/nginx/conf.d/fastapi.conf
```

Windows, trecho do `C:\nginx\conf\nginx.conf` depois da alteração:

```nginx
http {
    include       mime.types;
    default_type  application/octet-stream;
    include       fastapi.conf;   # <- linha adicionada
    ...
}
```

#### O que cada parte do arquivo faz

| Diretiva | Função |
|---|---|
| `limit_req_zone ... rate=10r/s` | Cria a regra de rate limiting: cada IP pode fazer 10 requisições por segundo |
| `limit_conn_zone` / `limit_conn conn_limit 20` | Limita a 20 as conexões simultâneas por IP |
| `upstream fastapi_backend` | Lista os servidores da aplicação (o Uvicorn). Com mais de um servidor, o Nginx faz o balanceamento de carga |
| `listen 8080` | Porta pública que o cliente acessa |
| `server_tokens off` | Esconde a versão do Nginx (dificulta ataques direcionados) |
| `client_max_body_size 1m` | Rejeita corpos de requisição maiores que 1 MB |
| `add_header X-Content-Type-Options / X-Frame-Options / Referrer-Policy` | Cabeçalhos de segurança HTTP |
| `gzip on` | Comprime as respostas JSON |
| `limit_req ... burst=20 nodelay` | Aplica o rate limiting e aceita picos curtos de até 20 requisições extras |
| `proxy_pass http://fastapi_backend` | Repassa a requisição para o Uvicorn |
| `proxy_set_header X-Real-IP / X-Forwarded-For / X-Forwarded-Proto` | Informa à API o IP real do cliente e o protocolo original |
| `proxy_*_timeout` | Tempo máximo de espera pela API |
| `error_page 429 / 502 503 504` | Devolve erros em JSON em vez da página HTML padrão do Nginx |
| `location = /nginx-health` | Health check respondido pelo próprio Nginx, sem passar pelo Python |

### 3.4 Subindo tudo

**1. Suba a API** (terminal 1), como na seção 2:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips="127.0.0.1"
```

**2. Valide e inicie o Nginx** (terminal 2):

Linux / WSL:

```bash
sudo nginx -t                    # testa a sintaxe da configuração
sudo systemctl restart nginx     # ou: sudo service nginx restart (no WSL)
```

Windows (dentro de `C:\nginx`):

```powershell
.\nginx.exe -t        # testa a configuração
start nginx           # inicia
.\nginx.exe -s reload # recarrega após alterar a configuração
.\nginx.exe -s stop   # para
```

O `nginx -t` deve mostrar `syntax is ok` e `test is successful`.

### 3.5 Testando

> No PowerShell, use `curl.exe` em vez de `curl`.

**a) O Nginx está de pé?**

```bash
curl http://localhost:8080/nginx-health
# nginx ok
```

**b) A API responde pelo Nginx?** Abra no navegador: <http://localhost:8080/docs>

**c) A requisição passou mesmo pelo proxy?** Compare o acesso direto com o acesso pelo Nginx:

```bash
curl http://127.0.0.1:8000/info    # direto no Uvicorn → "passou_pelo_nginx": false
curl http://localhost:8080/info    # pelo Nginx       → "passou_pelo_nginx": true, com x_real_ip preenchido
```

**d) CRUD passando pelo Nginx:**

```bash
curl -X POST http://localhost:8080/registros \
     -H "Content-Type: application/json" \
     -d '{"titulo": "Teste via Nginx", "descricao": "Criado pelo proxy reverso"}'

curl http://localhost:8080/registros
curl -X PUT http://localhost:8080/registros/1 -H "Content-Type: application/json" -d '{"titulo": "Editado"}'
curl -X DELETE http://localhost:8080/registros/1 -i
```

**e) Rate limiting.** O script dispara 60 requisições simultâneas:

```bash
python scripts/teste_rate_limit.py
```

Resultado esperado (aproximado): algumas passam e o restante é barrado pelo Nginx com **429**, sem chegar no Python.

```
60 requisições para http://localhost:8080/health
  HTTP 200: 21
  HTTP 429: 39
```

**f) API fora do ar.** Pare o Uvicorn (Ctrl+C) e acesse `http://localhost:8080/registros`. O Nginx responde:

```json
{"detail": "API indisponivel no momento."}
```

### 3.6 Bônus: balanceamento de carga

Para ver o Nginx distribuindo a carga entre duas instâncias da API:

1. Em `nginx/fastapi.conf`, descomente a linha `server 127.0.0.1:8001;` dentro do `upstream`, copie o arquivo de novo e recarregue o Nginx.
2. Suba duas instâncias, cada uma em um terminal:

```bash
# Linux/macOS
INSTANCIA=api-1 uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
INSTANCIA=api-2 uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --proxy-headers

# Windows (PowerShell)
$env:INSTANCIA="api-1"; uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
$env:INSTANCIA="api-2"; uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --proxy-headers
```

3. Chame `curl http://localhost:8080/health` várias vezes. O campo `instancia` alterna entre `api-1` e `api-2`, porque o Nginx usa *round-robin* por padrão. O cabeçalho `X-Instancia` também mostra quem respondeu.

Se uma das instâncias cair, o Nginx passa a mandar tudo para a outra. Isso é **tolerância a falhas** na prática.

### 3.7 Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `502 Bad Gateway` / "API indisponivel" | Uvicorn não está rodando na porta 8000 | Suba a API antes de testar |
| `bind() to 0.0.0.0:8080 failed` | Porta 8080 já está em uso | Feche o outro programa ou troque o `listen` para outra porta |
| `nginx -t` acusa `unknown directive` | Arquivo copiado com erro ou fora do bloco `http` | Confira o `include` (Windows) ou o local do arquivo |
| Alteração no `.conf` não fez efeito | Nginx não foi recarregado | `sudo systemctl reload nginx` ou `nginx -s reload` |
| No Windows, o Nginx não para | Processos ainda abertos | `.\nginx.exe -s stop` ou `taskkill /f /im nginx.exe` |

---

## 4. Referências

- NGINX Reverse Proxy Guide: <https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/>
- FastAPI: Behind a Proxy: <https://fastapi.tiangolo.com/advanced/behind-a-proxy/>
- FastAPI: Server Workers: <https://fastapi.tiangolo.com/deployment/server-workers/>
- NGINX Rate Limiting: <https://www.nginx.com/blog/rate-limiting-nginx/>
- TANENBAUM, A. S.; VAN STEEN, M. *Sistemas Distribuídos: Princípios e Paradigmas*. 2. ed. São Paulo: Pearson Prentice Hall, 2007. (Arquitetura de software, middleware e servidores proxy)
