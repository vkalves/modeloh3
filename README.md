# MiniMax H3 V2 no RunPod

Instala o ComfyUI **v0.38.0**, os pesos MiniMax H3, SAM3.1 e o workflow atual **H3 Prompt Único V2**. Sem LoRA e sem serviço de geração externo.

A V2 é genérica: ela não fica presa a um vídeo ou personagem específico. O usuário define quem editar, quais regiões regenerar, o que proteger e o prompt completo do H3.

**[Tutorial completo: instalação, atualização e solução de erros](docs/INSTALACAO_E_ERROS.md)** — comandos para o terminal do Pod e causas possíveis de erros de instalação, vídeo preto, memória, máscara, referências e exportação.

## Proteções contra vídeo preto

- O instalador e o launcher conferem o suporte ao VAE H3 INT8/convrot no código do ComfyUI usado.
- `verify.sh` também confere o SHA256 do VAE de vídeo, além dos outros três pesos H3 registrados.
- O workflow usa `H3SafeVAEDecode`: rejeita latentes/pixels com NaN/Inf e vídeos inteiros pretos antes de salvar a geração bruta ou compor o resultado final.
- O launcher foi corrigido para executar sem o caractere nulo que existia em seu código.

Essas proteções detectam falhas específicas. Elas não garantem a qualidade visual ou a troca de identidade. Após atualizar, execute `install.sh`, reinicie com `start.sh` e carregue novamente o JSON instalado; um workflow já aberto pode continuar usando a versão antiga.

## O que mudou na V2

- `[PESSOA]` identifica **quem** será editado no vídeo.
- `[EDITAR]` define **o que** será regenerado, uma região por linha: `face`, `hair`, `clothing`, `whole person` etc.
- `[PROTEGER]` lista objetos ou regiões que devem permanecer intactos.
- `[PROMPT]` recebe o prompt completo enviado ao H3.
- A máscara das regiões de edição é criada separadamente e intersectada com a pessoa alvo.
- A área editável é neutralizada somente na referência de movimento enviada ao H3, reduzindo a competição da identidade original com as fotos novas.
- O vídeo original continua sendo a base latente e a composição final.
- O workflow salva três diagnósticos: máscara vermelha, referência de movimento sanitizada e geração bruta.
- O workflow V2 foi validado em geração real no RunPod.

## 1. Prepare o Pod

- Use um template com **Python, Git, venv e terminal/Jupyter funcionando**.
- Use armazenamento que aceite Git, `chmod`, renomeação e links.
- Reserve espaço para os modelos H3, SAM3.1, PyTorch e dependências.
- Ao trocar de Pod, conecte o mesmo armazenamento antes de remover o Pod antigo.
- Se a porta 8188 já estiver sendo usada pelo ComfyUI do template, pare esse processo antes de iniciar o H3.

## 2. Instale

Em uma instalação nova:

```bash
cd /workspace &&
git clone https://github.com/vkalves/modeloh3.git &&
cd /workspace/modeloh3 &&
bash install.sh
```

Destino padrão:

```text
/workspace/ComfyUI-H3
```

O ambiente Python usado pelo projeto fica em:

```text
/workspace/ComfyUI-H3/.venv-h3
```

O instalador reaproveita arquivos e cache já existentes quando possível. Não apague os modelos para corrigir um erro de dependência ou de workflow.

## 3. Atualizar uma instalação existente

Pare o processo do ComfyUI H3 e execute:

```bash
cd /workspace/modeloh3
git pull --ff-only
bash install.sh
```

O instalador faz backup das versões anteriores dos nós/workflow antes de copiar a versão atual.

## 4. Iniciar o ComfyUI correto

```bash
cd /workspace/modeloh3
bash start.sh
```

Aguarde:

```text
COMFYUI H3 V2 PRONTO
```

Abra a porta **8188** no RunPod. Deixe o terminal aberto; `Ctrl+C` encerra o servidor.

Se a porta 8188 estiver ocupada, o script mostra os processos encontrados e não encerra nada automaticamente. Também é possível usar outra porta:

```bash
PORT=8189 bash start.sh
```

## 5. Workflow atual

O workflow instalado é:

```text
/workspace/ComfyUI-H3/user/default/workflows/H3_PROMPT_UNICO_V2.json
```

No bloco **03 - PEDIDO UNIVERSAL**, use esta estrutura:

```text
[PESSOA]
describe the target person in the source video

[EDITAR]
face
hair

[PROTEGER]
hands

[PROMPT]
Write the complete H3 edit prompt here. Use @Video1 for the source video and @Image1, @Image2, etc. for loaded reference images.
```

### Regras importantes

- `[PESSOA]` serve somente para localizar a pessoa correta.
- `[EDITAR]` controla a área que realmente pode ser regenerada.
- Use uma região por linha em `[EDITAR]`.
- Confira sempre a prévia vermelha antes da geração final.
- `@Image1`, `@Image2` etc. seguem a ordem das fotos realmente carregadas; slots vazios são ignorados.
- `@Video1` é convertido internamente para a referência de vídeo do H3.
- O áudio original é preservado quando presente.
- Para testes, comece com 3 segundos e resolução 672 antes de aumentar a duração.

## 6. Saídas de diagnóstico

Além do resultado final, a V2 salva:

```text
video/H3_PREVIA_MASCARA
video/H3_PREVIA_GERACAO_BRUTA
video/H3_PREVIA_REFERENCIA_SANITIZADA
```

Essas três saídas ajudam a identificar se um problema está na máscara, na geração do H3 ou na composição final.

## 7. Verificar arquivos

```bash
cd /workspace/modeloh3
bash verify.sh
```

A verificação confere ambiente, dependências, arquivos de modelo, os dois pacotes de nós personalizados e o JSON do workflow atual. Ela não mede qualidade visual.

Para instalar em outro caminho:

```bash
COMFY_DIR=/workspace/MeuComfyH3 bash install.sh
```

## Estrutura dos nós personalizados

A V2 usa dois pacotes locais do próprio repositório:

```text
custom_nodes/ComfyUI-H3-Reusable
custom_nodes/H3-Prompt-Unico-V2
```

O primeiro contém a preparação do vídeo, latente mascarado, composição e salvamento do prompt. O segundo contém o pedido universal V2, referências manuais, máscara por pessoa + regiões e a referência de movimento sanitizada.
