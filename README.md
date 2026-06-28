# One Drive Simplificado

Sistema de sincronização de arquivos distribuído em arquitetura Peer-to-Peer (P2P), desenvolvido como trabalho da disciplina de Redes de Computadores. O projeto usa sockets UDP e TCP para simular uma rede local de nós que descobrem uns aos outros automaticamente e mantêm diretórios sincronizados.

## Visão Geral

Cada nó executa três serviços principais:

- **Descoberta de peers via UDP broadcast:** os nós anunciam sua presença na rede e mantêm uma tabela de peers ativos.
- **Monitoramento do diretório local:** alterações, criações e exclusões em `/app/documents` são detectadas periodicamente.
- **Sincronização via TCP:** arquivos são listados, baixados, enviados, atualizados ou removidos entre os peers.

Quando um novo nó entra na rede, ele consulta os arquivos disponíveis nos peers já conhecidos e baixa os arquivos ausentes ou divergentes. Depois disso, mudanças locais são propagadas para os demais nós.

## Funcionalidades

- Descoberta automática de nós na rede local com UDP broadcast.
- Heartbeat simples para detectar nós desconectados por timeout.
- Sincronização inicial entre peers ao descobrir um novo nó.
- Propagação de arquivos criados ou modificados.
- Propagação de exclusões.
- Verificação de integridade com hash SHA-256.
- Detecção de conflitos com base no hash anterior do arquivo.
- Merge textual automático quando possível.
- Marcação de conflitos no arquivo quando a resolução automática não é segura.
- Logs padronizados no terminal com horário, nó, categoria e severidade.

## Tecnologias

- Python 3.11
- Docker e Docker Compose
- UDP para descoberta de peers
- TCP para transferência e comandos de sincronização
- Bibliotecas padrão do Python: `socket`, `threading`, `json`, `hashlib`, `os`, `difflib`

## Estrutura do Projeto

```text
simplified_onedrive/
├── Dockerfile
├── docker-compose.yml
├── README.md
├── documents/
│   ├── documents_node_a/
│   ├── documents_node_b/
│   ├── documents_node_c/
│   └── documents_node_d/
└── src/
    ├── main.py
    ├── core/
    │   ├── file_monitor.py
    │   ├── node.py
    │   └── terminal_ui.py
    ├── network/
    │   ├── discovery.py
    │   └── sync_service.py
    └── utils/
        └── merge.py
```

## Como Executar

Pré-requisitos:

- Docker instalado
- Docker Compose instalado

Suba dois nós:

```bash
docker compose up node_a node_b --build
```

Para deixar os logs mais limpos, sem o prefixo do container:

```bash
docker compose up node_a node_b --build --no-log-prefix
```

Em outro terminal, adicione um terceiro nó:

```bash
docker compose up node_c --no-log-prefix
```

Também existe um quarto nó configurado:

```bash
docker compose up node_d --no-log-prefix
```

Para encerrar a rede:

```bash
docker compose down
```

## Testes Manuais

Com os nós em execução, crie um arquivo no `node_a`:

```bash
docker compose exec node_a sh -c "echo 'arquivo criado no node_a' > /app/documents/teste_a.txt"
```

Verifique se ele foi replicado:

```bash
docker compose exec node_b cat /app/documents/teste_a.txt
docker compose exec node_c cat /app/documents/teste_a.txt
```

Altere o arquivo a partir de outro nó:

```bash
docker compose exec node_b sh -c "echo 'alterado pelo node_b' >> /app/documents/teste_a.txt"
docker compose exec node_a cat /app/documents/teste_a.txt
```

Teste a exclusão:

```bash
docker compose exec node_a rm /app/documents/teste_a.txt
docker compose exec node_b ls /app/documents
```

## Conflitos

O sistema usa o hash anterior do arquivo para decidir se uma alteração remota pode sobrescrever a versão local com segurança.

Quando dois nós alteram o mesmo arquivo de formas incompatíveis, o conteúdo pode receber marcadores de conflito. Eles seguem o formato abaixo, com linhas de início, separação e fim envolvendo as versões em disputa:

```text
[inicio: ALTERACOES DA REDE]
+ conteudo recebido de outro no
[separador]
- conteudo local
[fim: SUAS ALTERACOES LOCAIS]
```

Depois de resolver manualmente o arquivo e remover os marcadores, uma nova alteração local pode ser propagada aos peers.

## Observações

- A sincronização atual envia arquivos inteiros, não deltas por chunks.
- A resolução de conflitos atual é baseada em hashes e merge textual, não em relógios vetoriais.
- O sistema foi pensado para simulação em rede Docker local.

## Identificação do Trabalho

**Trabalho 2:** Mini-One Drive  
**Disciplina:** CIC0124 Redes de Computadores

### Autores

- Felipe Lauterjung Caselli - 24/1032401
- Laíssa Beatriz Soares da Silva - 22/2032982
- Marcio Vinicius da Silva Guimaraes - 24/2001553
- Pedro Fernandes de Oliveira - 23/1006177
