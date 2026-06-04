# One Drive Simplificado

Este projeto consiste em um sistema de sincronização de arquivos distribuído, em uma arquitetura Peer-to-Peer (P2P). Foi desenvolvido com foco na alta disponibilidade, tolerância a falhas e resolução descentralizada de conflitos. 

O sistema foi construído como estudo de caso para a disciplina de Redes de Computadores, aplicando de forma prática conceitos de comunicação em rede com a construção de Socket's.

---

## 1. Visão Geral do Sistema

O Mini-OneDrive emula o comportamento de plataformas modernas de armazenamento em nuvem, substituindo a tradicional arquitetura Cliente-Servidor por uma rede 100% descentralizada. A topologia permite que qualquer nó integre ou abandone a rede de forma dinâmica, garantindo que a sincronização dos dados entre os pares ocorra de forma autônoma.

### Principais Funcionalidades

* **Descoberta Dinâmica (UDP Broadcast):** Detecção automática de nós na rede local (LAN), operando sem a necessidade de um servidor centralizado de registros ou da configuração manual de endereços IP.
* **Tolerância a Falhas (Heartbeat):** Mecanismo de monitoramento contínuo do estado da rede. Em caso de desconexão abrupta de um nó, o sistema detecta a ausência por limite de tempo (*timeout*) e atualiza a topologia em tempo real.
* **Monitoramento do Sistema de Arquivos:** Registro e acompanhamento dinâmico das operações de criação, modificação e exclusão de arquivos nos diretórios locais designados.
* **Resolução de Conflitos (Relógios Vetoriais - Em desenvolvimento):** Implementação de controle de causalidade para gerenciar edições simultâneas *offline*, prevenindo a perda de dados através da criação de versões de conflito.
* **Sincronização Delta (TCP - Em desenvolvimento):** Protocolo de transferência otimizada de dados, baseado na segmentação de arquivos (*chunks*) e na verificação de integridade através de algoritmos de *hash* (SHA-256).

---

## 2. Tecnologias Utilizadas

A arquitetura do projeto priorizou a minimização de dependências externas, recorrendo exclusivamente aos recursos nativos da linguagem para a lógica principal:

* **Linguagem de Programação:** Python 3.11 (Uso das bibliotecas padrão: `socket`, `threading`, `json`, `hashlib`, `os`).
* **Ambiente e Virtualização:** Docker e Docker Compose.
* **Protocolos de Comunicação:** UDP (Gestão de topologia e descoberta) e TCP (Transferência confiável de dados).

---

## 3. Estrutura do Projeto

A organização dos diretórios reflete a separação entre a infraestrutura de execução, os dados persistentes e a lógica de domínio:

```text
simplified_onedrive/
├── docker-compose.yml      # Configuração da orquestração dos contêineres
├── Dockerfile              # Definição da imagem base da aplicação
├── documents/              # Diretórios locais mapeados para sincronização
│   ├── documents_node_a/
│   ├── documents_node_b/
│   └── documents_node_c/
└── src/
    ├── main.py             # Ponto de entrada da aplicação
    ├── core/
    │   └── node.py         # Classe principal (Composição de serviços do Nó)
    └── network/
        └── discovery.py    # Implementação do protocolo de descoberta P2P

---

## 4. Instruções de Execução

O sistema é executado em um ambiente isolado através do Docker, o que permite a simulação de uma rede composta por múltiplos dispositivos na mesma máquina.

### Pré-requisitos
* Docker instalado no sistema *host*.
* Docker Compose configurado.

### Procedimento de Inicialização

**Passo 1: Clonar o repositório**
```bash
git clone [https://github.com/pedrofernandss/simplified_onedrive.git](https://github.com/pedrofernandss/simplified_onedrive.git)
cd simplified-onedrive
```

**Passo 2: Iniciar a topologia base**
Para instanciar os dois primeiros nós e estabelecer a rede primária, execute:
```bash
docker compose up node_a node_b --build
```
*Nota: O terminal apresentará os logs da inicialização, demonstrando a descoberta mútua via protocolo UDP.*

**Passo 3: Testar a escalabilidade dinâmica**
Para verificar a capacidade de integração em tempo real, abra uma nova janela de terminal no mesmo diretório e inicie um terceiro nó:
```bash
docker compose up node_c
```
*Nota: O Nó C emitirá um pacote de anúncio (broadcast), sendo imediatamente reconhecido e integrado pelos Nós A e B em suas tabelas de pares.*

**Passo 5: Encerrar o sistema**
Para terminar a execução e remover os recursos temporários de rede, utilize o comando:
```bash
docker compose down
```
