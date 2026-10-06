# MiniMax H3 no RunPod

Instala o ComfyUI **v0.38.0**, os pesos H3, SAM3.1 e o workflow com máscara corrigida. Sem LoRA e sem serviço de geração externo.

## 1. Prepare o Pod

- Use um template com **Python, Git, venv e acesso ao terminal**. Confira se o Jupyter realmente abre antes de instalar.
- Se os logs mostram `.venv-cu128/bin/activate: No such file or directory`, o template tem um ambiente ausente. Esperar pelo download do H3 não corrige esse problema.
- Use um disco que aceite Git, permissões (`chmod`) e links. O erro `config.lock ... Operation not permitted` aconteceu no volume usado na instalação anterior. O script agora testa essas operações antes de baixar o ComfyUI.
- Reserve espaço para os cinco modelos, PyTorch e dependências. O instalador consulta os tamanhos dos modelos e verifica espaço livre antes de baixá-los. Um `df` com capacidade virtual, como `1.0P`, não confirma a cota real: confira o painel do RunPod.
- Ao trocar de Pod/GPU, confirme que os arquivos estarão no novo Pod antes de excluir o antigo. Não há migração automática de disco local.

Uma GPU menor pode servir para baixar e verificar arquivos. Isso **não comprova** que ela consegue gerar vídeo.

## 2. Instale

No terminal do JupyterLab ou Code Server, cole o bloco inteiro:

```bash
cd /workspace &&
git clone https://github.com/vkalves/modeloh3.git &&
cd /workspace/modeloh3 &&
bash install.sh
```

Os `&&` impedem continuar se o clone falhar. Se a pasta `modeloh3` já existe, use a atualização abaixo.

O destino padrão é `/workspace/ComfyUI-H3`. O Python fica em **`.venv-h3` dentro dessa pasta**. Um ambiente antigo ativado no terminal não é reutilizado. Na primeira instalação, PyTorch também pode precisar de um download grande.

As etapas são numeradas. A cada 20 segundos, uma mensagem informa que o comando ainda executa; isso não significa que o download avançou. Veja também as barras de download e o log indicado na tela. Avisos de token ausente não são, por si só, falhas; erros de acesso/download interrompem o script.

Se houver erro, leia a última mensagem e corrija a causa. Depois execute `bash install.sh` novamente. Não apague os modelos: o Hugging Face aproveita os arquivos/cache disponíveis. O instalador guarda backups do nó e do workflow antes de substituir esses arquivos.

## 3. Abra o ComfyUI correto

```bash
cd /workspace/modeloh3
bash start.sh
```

Aguarde **COMFYUI H3 PRONTO**. Abra a porta **8188** no painel do RunPod. Deixe o terminal aberto; `Ctrl+C` encerra esse servidor.

O comando usa a pasta e o Python da instalação H3, verifica CUDA e consulta os nós carregados pelo servidor. Não basta aparecer “instalação concluída”: o servidor precisa passar por essa etapa.

**Porta ocupada:** o script informa o conflito e as pastas dos processos ComfyUI encontrados. Não encerra nada automaticamente. Pare a instalação antiga pelo terminal dela e repita. Se o template reinicia o serviço antigo automaticamente, configure seu serviço ou use outra porta:

```bash
PORT=8189 bash start.sh
```

Nesse caso, exponha a porta **8189 como HTTP no RunPod** e abra essa porta. Reiniciar pelo Manager de uma instalação antiga não inicia a instalação H3.

Abra o workflow:

```text
/workspace/ComfyUI-H3/user/default/workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json
```

## Atualizar ou verificar

Pare o servidor H3 antes de atualizar. Na pasta do repositório:

```bash
git pull --ff-only && bash install.sh
```

Para verificar os arquivos novamente:

```bash
bash verify.sh
```

A verificação usa o mesmo Python, confere dependências e a versão, calcula SHA256 de três pesos registrados em `models.sha256` e verifica a presença dos demais. A leitura de arquivos grandes pode demorar. Ela não é um teste de geração.

Para destino diferente, na instalação:

```bash
COMFY_DIR=/workspace/MeuComfyH3 bash install.sh
```

Após uma instalação bem-sucedida, esse destino fica salvo localmente para `start.sh`, `verify.sh` e próximas instalações. `COMFY_DIR` explícito sempre tem prioridade. Ao mover o repositório para outro Pod, confira esse caminho.

## Usar o workflow

- Comece com um trecho curto, por exemplo 3 segundos. O workflow vem com 15 segundos e lado maior de 672 pixels; ajuste a duração ao vídeo.
- Carregue o vídeo e somente as referências necessárias; deixe as outras em `(VAZIO - ignorar)`.
- Descreva a função de cada referência no próprio slot. Confira a ordem das imagens carregadas e o prompt salvo; não reutilize números `Image 1/2` de outro caso sem conferir.
- Preencha os cinco campos do pedido: alvo, mudança, preservação, uso das referências e objetos protegidos. Substitua os exemplos de outro vídeo.
- Confira a máscara vermelha, principalmente ao trocar somente rosto e cabelo. Um prompt sozinho não garante que a máscara selecione apenas a cabeça.
- O resultado é composto sobre as dimensões originais, a 24 fps. O áudio original é encaminhado quando presente.

**Estado dos testes:** os scripts têm testes locais sem GPU. A instalação completa, o consumo de memória e a geração precisam ser confirmados no RunPod; não há garantia de qualidade da troca só porque o servidor abriu.

## Erros observados e prevenção

| Problema anterior | Mudança |
| --- | --- |
| Git falhava por permissões no volume | Teste de chmod, renomeação, links e Git antes do clone do ComfyUI |
| Python de outra instalação era usado | Ambiente `.venv-h3` próprio e compartilhado pelos três comandos |
| Longa espera sem indicação | Etapas, mensagens periódicas e logs em `logs/` |
| Porta 8188 abria ComfyUI 0.30.0 | `start.sh` aponta para o H3 e detecta porta ocupada |
| “Concluído” mesmo sem abrir o servidor | Mensagens separadas para arquivos verificados e servidor pronto |
| Reinício não carregava os nós certos | Conferência dos tipos de nó do workflow em `/object_info` |

Erros de criação do contêiner, Jupyter indisponível e configurações de portas do RunPod acontecem antes ou fora deste instalador. O script não consegue corrigir o host do RunPod.
