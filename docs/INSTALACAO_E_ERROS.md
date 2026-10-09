# H3 no RunPod: instalação e solução de erros

Cole os comandos no **terminal do Jupyter ou do Code Server do Pod**. Não cole no campo de prompt do ComfyUI. Execute um bloco por vez e espere terminar.

## 1. Antes de instalar

- Conecte o armazenamento que contém seus modelos. Se os arquivos já estão nele, não apague nem baixe tudo de novo.
- Use um Pod com GPU NVIDIA e um template com Python, Git, venv e terminal funcionando.
- O destino padrão é `/workspace/ComfyUI-H3`. O ambiente Python é `.venv-h3`, dentro desse destino.
- Confira a GPU e o espaço disponível:

```bash
nvidia-smi
df -h /workspace
```

O instalador calcula o espaço necessário para os pesos que faltam, com margem. O espaço para Python e dependências também é necessário. Em armazenamento virtual, confira a capacidade real no painel do RunPod.

## 2. Instalação nova ou atualização

Se já há um ComfyUI H3 aberto, pare-o com `Ctrl+C` **no terminal que está executando esse servidor**, antes de instalar. O instalador recusa alterar a instalação se encontrar esse processo ativo.

Este bloco serve para instalar ou atualizar, sem apagar arquivos:

```bash
cd /workspace
if [ -d /workspace/modeloh3/.git ]; then
  git -C /workspace/modeloh3 pull --ff-only
else
  git clone https://github.com/vkalves/modeloh3.git /workspace/modeloh3
fi
```

Se esse bloco terminou sem erro, execute:

```bash
cd /workspace/modeloh3
bash install.sh
```

Espere aparecer `ARQUIVOS V2 INSTALADOS E VERIFICADOS`. Isso ainda não inicia o servidor.

O instalador fixa o ComfyUI em **v0.38.0**, confere o suporte ao VAE H3 INT8/convrot, usa um ambiente Python separado e verifica os hashes dos quatro pesos H3 registrados, incluindo o VAE de vídeo. O arquivo SAM3.1 é verificado quanto à presença; não há hash dele registrado neste projeto.

As versões anteriores dos nós e do workflow ficam em `/workspace/ComfyUI-H3/h3_backups/`. Seus vídeos de entrada e resultados não são removidos.

Se usar outro destino, defina-o na instalação:

```bash
cd /workspace/modeloh3
COMFY_DIR=/workspace/MeuComfyH3 bash install.sh
```

Depois de uma instalação bem-sucedida, o projeto lembra esse destino. Para selecionar explicitamente outro destino nos comandos seguintes, use a mesma variável `COMFY_DIR`.

## 3. Abrir a instalação correta

```bash
cd /workspace/modeloh3
bash start.sh
```

Espere `COMFYUI H3 V2 PRONTO`. Abra a porta HTTP **8188** no RunPod e deixe esse terminal aberto. Fechar ou interromper o processo encerra o servidor.

Se a porta estiver ocupada, o script informa o problema e não encerra processos automaticamente. Pare o servidor antigo pelo terminal dele ou use outra porta:

```bash
cd /workspace/modeloh3
PORT=8189 bash start.sh
```

Nesse caso, exponha e abra a porta **8189**, não a 8188.

Não use o botão de outro ComfyUI do template como substituto de `start.sh`: ele pode abrir uma instalação diferente, com outras dependências.

## 4. Carregar o workflow atualizado

Abra ou importe este arquivo no ComfyUI:

```text
/workspace/ComfyUI-H3/user/default/workflows/H3_PROMPT_UNICO_V2.json
```

Se o destino é personalizado, substitua `/workspace/ComfyUI-H3` pelo seu destino.

Atualizar o repositório não atualiza automaticamente o workflow que já estava aberto no navegador. Depois de `install.sh` e da reinicialização, carregue o JSON instalado novamente. Guarde seu prompt e suas escolhas antes de substituir a tela antiga.

O nó de decodificação atualizado se chama **DECODIFICAR H3 — PROTECAO CONTRA PRETO / NaN**, tipo `H3SafeVAEDecode`. Ele alimenta tanto a geração bruta quanto a composição final.

## 5. Primeiro teste

1. Carregue o vídeo original e suas fotos de referência.
2. Comece com **3 segundos**, resolução **672**, scheduler `normal`, **20 passos** e denoise **1.0**, como no JSON padrão.
3. Preencha o pedido com as quatro seções abaixo. Escreva uma região por linha em `[EDITAR]`.
4. Confira se a área vermelha cobre o que pretende editar e se a pessoa selecionada está correta.
5. Confira o resultado curto antes de aumentar a duração ou a resolução. Isso reduz o custo de investigar um erro.

```text
[PESSOA]
the seated woman wearing the brown dress

[EDITAR]
face
hair

[PROTEGER]
hands

[PROMPT]
Edit @Video1 by replacing only the face and hair of the selected woman with the identity from @Image1. Preserve the original body, clothing, hands, actions, camera, timing, lighting and background.
```

Este exemplo usa uma foto. Se carregar mais fotos, descreva o papel de cada referência no seu prompt. `@Image1`, `@Image2` etc. seguem a ordem das fotos realmente carregadas; slots vazios são ignorados. Uma referência inexistente pode provocar erro na validação.

## 6. Vídeo preto: o que foi corrigido

Há duas proteções diferentes:

- **Compatibilidade:** instalação, verificação e inicialização conferem se o código instalado tem o caminho de carregamento do VAE H3 quantizado. A etiqueta da versão sozinha não é suficiente.
- **Resultado inválido:** antes da decodificação, o workflow rejeita latentes com NaN/Inf. Depois dela, rejeita pixels inválidos e vídeos inteiros praticamente zerados. A composição final também faz a verificação, para não esconder uma geração preta atrás do vídeo original.

`NaN/Inf` significa valores numéricos inválidos. `H3_VIDEO_PRETO` significa que o vídeo decodificado inteiro ficou preto. Essas mensagens interrompem a saída; não substituem a geração por um vídeo falso nem provam que a identidade foi trocada.

Cenas escuras e cortes com alguns frames pretos continuam permitidos. Uma fonte realmente toda preta pode disparar a proteção. A proteção não detecta todos os artefatos visuais ou pixels pretos apenas em parte da imagem.

## 7. Erros de instalação e inicialização

| Mensagem ou sintoma | Possível causa | O que fazer |
|---|---|---|
| `git: command not found`, Python ou venv ausente | Template sem a ferramenta necessária | Use um template com essas ferramentas ou instale a ferramenta faltante antes de repetir. |
| `Operation not permitted`, erro de chmod ou links | A pasta não aceita operações exigidas pelo Git/venv | Escolha um destino com suporte a essas operações. Não repita downloads na mesma pasta com esse erro. |
| `No space left on device` ou espaço insuficiente | Disco/cache sem espaço | Confira `df -h` e o painel do armazenamento; aumente o espaço ou remova apenas arquivos que sabe que não precisa. |
| Timeout, erro de rede ou download interrompido | Conexão com GitHub/Hugging Face falhou | Resolva a conexão e repita `install.sh`. O cache é reaproveitado quando possível. |
| HTTP 401/403 no Hugging Face | Restrição de acesso, autenticação ou rede | Confira acesso ao arquivo e a mensagem exata. Se precisar de token, configure `HF_TOKEN` no Pod; não publique o token. |
| `ComfyUI tem alteracoes locais` ou `git pull --ff-only` falha | Código local alterado ou histórico divergente | Preserve suas alterações e compare o conflito. Não use `reset --hard` sem saber o que será descartado. |
| `Ambiente H3 ausente` | Instalação incompleta ou destino diferente | Confira o destino mostrado e execute `install.sh` no repositório certo. |
| Versão diferente ou `sem suporte ao VAE H3 INT8/convrot` | ComfyUI antigo, modificado ou instalação errada | Pare o servidor e repita `install.sh`; depois abra com `start.sh`. |
| Porta 8188 ocupada | Outro servidor está usando a porta | Pare-o pelo terminal dele ou use `PORT=8189` e abra a porta correspondente. |
| Nós ausentes ou vermelhos no workflow | Nós não carregaram, JSON antigo ou dependência falhou | Leia o log, execute `install.sh`, reinicie e importe o JSON atualizado. |
| Servidor não respondeu em 180s | Inicialização falhou ou excedeu o tempo | Leia o log de início. Não conclua que é erro de prompt, pois a geração ainda não começou. |
| `CUDA indisponivel` | Pod sem GPU, driver ou Torch sem CUDA | Confira `nvidia-smi` e `verify.sh`. Não altere o prompt para corrigir CUDA. |
| `no kernel image` ou `invalid device function` | Torch/kernel não compatível com a GPU | Registre GPU, versão de Torch e erro completo; confira suporte da combinação antes de trocar pacotes. |

## 8. Erros na geração

| Sintoma | Possíveis causas | Como separar o problema |
|---|---|---|
| `H3_VIDEO_PRETO`, vídeo totalmente preto ou ruído colorido | VAE incompatível/incorreto, pesos corrompidos ou falha numérica; fonte toda preta também pode disparar a proteção | Execute `verify.sh`, confira a instalação aberta e os dois VAEs. Se tudo passar, use o log da geração para investigar; não presuma que é a máscara. |
| `NaN/Inf` | Falha numérica no sampler ou VAE, pesos ou ambiente problemáticos | A mensagem identifica se falhou no latente, na codificação ou na saída do VAE. Confira arquivos e dependências antes de repetir. |
| `CUDA out of memory` | Resolução/duração alta ou outra tarefa ocupando VRAM | Confira `nvidia-smi`, reduza para o teste de 3s/672 e encerre tarefas concorrentes que você iniciou. Persistindo, precisa de mais memória ou revisão do ambiente. |
| Erro em `03 - PEDIDO UNIVERSAL` | Seção obrigatória ausente ou pedido inválido | Use `[PESSOA]`, `[EDITAR]`, `[PROTEGER]`, `[PROMPT]` e leia a mensagem. Essa tentativa pode nem ter começado a gerar. |
| Seleção vazia ou pessoa errada | Descrição ambígua ou rastreamento SAM falhou | Confira `H3_PREVIA_MASCARA` e ajuste a descrição da pessoa/regiões. |
| Rosto não muda, mas vídeo é salvo | Referências/condicionamento não aplicados ou composição encobrindo o resultado | Compare geração bruta e final da mesma tentativa. Se a bruta já falha, investigue antes da composição. Se só o final perde a troca, investigue máscara/composição. |
| Cenário muda ou bordas ficam estranhas | Máscara ampla, proteção insuficiente ou artefato na geração | Compare máscara, referência sanitizada e geração bruta. |
| Nome diz 20 passos, mas o campo mostra 12 | Configuração alterada na tela | O valor do campo é o que executa. A diferença sozinha não prova a causa de uma falha. |
| Falta áudio | Fonte sem áudio ou falha de leitura/recorte | Confira o arquivo original e o log. O resultado final reutiliza o áudio original quando presente. |
| Erro ao salvar | Espaço, permissão, caminho ou codificação de vídeo | Confira pasta de saída, espaço e a última mensagem do log; não reinstale pesos por um erro de exportação. |

## 9. Verificar e guardar evidências

```bash
cd /workspace/modeloh3
bash verify.sh
```

A verificação de hashes lê arquivos grandes e pode demorar. Ela confere arquivos/dependências; não mede qualidade visual nem prova que a GPU gerou corretamente.

Logs de instalação/início: `/workspace/modeloh3/logs/`. As mensagens da geração aparecem no terminal do servidor e no log de início quando aberto por `start.sh`.

Saídas padrão: `/workspace/ComfyUI-H3/output/video/`, com prefixos:

- `H3_PREVIA_MASCARA`: área selecionada em vermelho.
- `H3_PREVIA_REFERENCIA_SANITIZADA`: referência enviada ao H3 com a área editável neutralizada.
- `H3_PREVIA_GERACAO_BRUTA`: resultado antes de compor com o original.
- `H3_REUTILIZAVEL`: composição final com áudio original quando presente.

Se a proteção interromper a decodificação, a bruta/final daquela tentativa não serão salvas. Arquivos de tentativas anteriores podem continuar na pasta. Confira os horários para não comparar tentativas diferentes.

Para pedir ajuda, guarde: erro completo, log, GPU, configuração usada, JSON realmente executado e, quando disponíveis, as prévias da **mesma tentativa**. Não envie tokens ou senhas.

### Se apenas o VAE de vídeo está corrompido

Use este bloco somente se `verify.sh` apontou hash incorreto desse arquivo. Pare o servidor primeiro. Ele força baixar apenas o VAE de vídeo; os outros modelos ficam preservados. Este comando usa o destino padrão:

```bash
/workspace/ComfyUI-H3/.venv-h3/bin/python - <<'PY'
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='Comfy-Org/MiniMax-H3',
    filename='vae/minimax_h3_video_vae_int8_convrot.safetensors',
    local_dir='/workspace/ComfyUI-H3/models',
    force_download=True,
)
PY
```

Depois execute `bash verify.sh` novamente. Para outro destino, ajuste os dois caminhos no bloco. Para outro peso corrompido, use o arquivo exato que a verificação apontou, sem apagar todos os modelos.

## Base técnica e limite da validação

O suporte ao VAE quantizado foi conferido no código oficial do ComfyUI v0.38.0:

- [Carregamento do VAE H3 e operações quantizadas](https://github.com/Comfy-Org/ComfyUI/blob/v0.38.0/comfy/sd.py).
- [Decoder do VAE H3 com operações configuráveis](https://github.com/Comfy-Org/ComfyUI/blob/v0.38.0/comfy/ldm/minimax/vae.py).
- [Pesos oficiais dos VAEs e metadados](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/vae).

Os testes automatizados deste repositório validam as proteções em CPU. Uma geração real no seu Pod continua necessária para confirmar que GPU, dependências, modelos e vídeo funcionam juntos. Nenhuma verificação garante ausência de todos os erros de geração.
