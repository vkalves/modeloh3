# Instalar uma vez e trocar para uma GPU mais forte

**Objetivo:** preparar o H3 em um Pod mais barato e reutilizar modelos, nós, workflow e ambiente no Pod de produção. O caminho mais simples é manter tudo no mesmo **Network Volume**, montado no mesmo lugar.

Não é possível garantir ausência de todos os erros. Com outro tipo de GPU, a compatibilidade de driver, Torch e kernels também precisa ser conferida. Este guia evita reinstalações e downloads de pesos desnecessários.

## 1. Escolha o armazenamento antes do primeiro Pod

No painel RunPod, use **Storage → New Network Volume**. Escolha um data center que ofereça tanto a GPU de instalação quanto a GPU de produção desejada. Na criação dos dois Pods, selecione **o mesmo volume pelo ID** e monte-o em `/workspace`.

| Armazenamento | Serve para esta migração? |
|---|---|
| Network Volume | Sim. É independente do Pod e pode ser usado em outro Pod compatível com sua localização. |
| Volume Disk do Pod | Não pelo simples ato de criar outro Pod. Os dados ficam associados ao Pod antigo. |
| Container Disk | Não. Não deve guardar a instalação que você pretende reutilizar. |

O caminho `/workspace` sozinho não prova que o armazenamento é um Network Volume. Confirme o ID do volume no painel. Em Pods, o Network Volume deve ser escolhido na criação; este roteiro usa Secure Cloud e o volume regional comum, não Global Volumes beta.

Se você **já tem** esse volume com a instalação funcionando, vá direto à seção 4. Não crie outro volume e não reinstale.

## 2. Crie o Pod de instalação

1. Selecione o Network Volume escolhido.
2. Escolha uma GPU mais barata disponível nesse local. Ela precisa de recursos suficientes para a instalação e verificação; não precisa conseguir gerar seu vídeo final.
3. Use um template com terminal/Jupyter, Git, Python, venv e ambiente CUDA compatível com as GPUs de origem e destino. A GPU mais barata não acelera os downloads: CPU, rede e armazenamento também influenciam.
4. Guarde o **ID do volume**, o template e a **imagem de container com versão exata**. Se disponível, guarde também seu digest. Não dependa de uma tag móvel como `latest`.
5. Exponha a porta HTTP **8188** e as portas do terminal/Jupyter exigidas pelo template. Não use o ComfyUI de outra pasta que o template possa iniciar automaticamente.

No terminal desse Pod, confira:

```bash
df -h /workspace
nvidia-smi
```

O primeiro comando mostra a montagem e o espaço. A identificação do volume deve ser confirmada também no painel. Reserve espaço para modelos, ambiente Python, entradas, saídas e backups; o instalador verifica espaço antes do download.

## 3. Instale uma única vez

**Somente se `/workspace/modeloh3` ainda não existir**, execute:

```bash
git clone https://github.com/vkalves/modeloh3.git /workspace/modeloh3
```

Depois:

```bash
cd /workspace/modeloh3 && bash install.sh
```

Espere terminar com `ARQUIVOS V2 INSTALADOS E VERIFICADOS`. A instalação já chama `verify.sh`; não é necessário repetir a leitura de todos os pesos se essa etapa acabou de passar.

A instalação padrão fica em:

```text
/workspace/modeloh3
/workspace/ComfyUI-H3
/workspace/ComfyUI-H3/.venv-h3
/workspace/ComfyUI-H3/models
/workspace/ComfyUI-H3/input
/workspace/ComfyUI-H3/output
/workspace/ComfyUI-H3/user/default/workflows
```

Todas essas pastas devem permanecer no volume. Se usou um destino personalizado, mantenha o mesmo caminho no Pod novo. O repositório guarda esse destino em `.h3-comfy-dir` após uma instalação concluída.

Se o Pod de instalação tiver capacidade suficiente, você pode iniciar com `bash start.sh`. A aprovação dos arquivos não exige uma geração longa em uma GPU fraca. Erro de memória durante uma geração não significa que você precisa baixar os pesos novamente.

## 4. Prepare a troca sem perder suas configurações

No Pod que já funciona:

1. Termine a geração atual e salve seu workflow com prompt, fotos, resolução, passos, seed e duração. Guarde também uma cópia do JSON no computador.
2. Confirme que os modelos, fotos, vídeos e o ambiente `.venv-h3` estão no volume, e não em um caminho externo por link simbólico. Você pode conferir o destino real com `readlink -f /workspace/ComfyUI-H3/.venv-h3` e `readlink -f /workspace/ComfyUI-H3/models`.
3. Anote a imagem exata do container, suas configurações de inicialização e o ID do Network Volume. A mesma etiqueta de template não garante que a imagem permaneceu igual.
4. Pare o **servidor ComfyUI** com `Ctrl+C` no terminal dele. Não instale, atualize ou gere simultaneamente nos dois Pods usando a mesma instalação.
5. Preserve o Pod antigo até conferir o novo. Não exclua o Network Volume.

Guarde um registro simples do ambiente, no terminal do Pod antigo:

```bash
cd /workspace/modeloh3
source scripts/common.sh
mkdir -p logs
git rev-parse HEAD > logs/repositorio-antes-da-troca.txt
git -C "$COMFY_DIR" rev-parse HEAD > logs/comfyui-antes-da-troca.txt
"$PYTHON" -m pip freeze > logs/pacotes-antes-da-troca.txt
"$PYTHON" -c 'import sys, torch; print(sys.version); print("Torch:", torch.__version__); print("CUDA do Torch:", torch.version.cuda); print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "indisponivel")' > logs/ambiente-antes-da-troca.txt
```

Esses arquivos são registros para comparação, não instaladores. Não publique senhas ou tokens junto dos logs.

## 5. Crie o Pod mais forte

Na criação do novo Pod:

- Selecione **o mesmo ID de Network Volume**, no local em que ele pode ser conectado.
- Escolha a GPU mais forte disponível e mantenha a montagem `/workspace`.
- Use a **mesma imagem de container com versão exata**, o mesmo caminho do Python e configurações de inicialização compatíveis. Evite scripts do template que reinstalem ou atualizem automaticamente uma pasta existente.
- Exponha novamente as portas necessárias, incluindo HTTP 8188.

No terminal do Pod novo, confira que suas pastas e arquivos conhecidos aparecem. Se `/workspace/modeloh3` ou os modelos não aparecem, pare aqui e confira volume/montagem. **Não rode o instalador para tentar fazer os arquivos aparecerem.**

O RunPod pode precisar baixar a imagem de container no novo host. Isso é diferente de baixar os pesos H3 de novo. Não há promessa de “nenhum download de qualquer tipo”.

## 6. Verifique e inicie sem reinstalar

Se as pastas estão corretas, execute este teste curto, que não baixa nada:

```bash
cd /workspace/modeloh3
source scripts/common.sh
nvidia-smi
"$PYTHON" -m pip check
"$PYTHON" scripts/sync_nodes.py --check "$COMFY_DIR"
"$PYTHON" - <<'PY'
import torch
assert torch.cuda.is_available(), 'CUDA indisponivel no novo Pod'
print('GPU:', torch.cuda.get_device_name(0))
print('Torch:', torch.__version__, '| CUDA:', torch.version.cuda)
x = torch.ones((256, 256), device='cuda', dtype=torch.float16)
y = x @ x
torch.cuda.synchronize()
assert bool(torch.isfinite(y).all()), 'Teste numerico da GPU falhou'
print('Teste basico de GPU aprovado. Ainda nao valida todos os kernels do H3.')
PY
```

**Só se todos os comandos terminarem sem erro**, inicie:

```bash
cd /workspace/modeloh3 && bash start.sh
```

Abra a porta 8188 **do Pod novo**. Aguarde `COMFYUI H3 V2 PRONTO`. Carregue seu JSON salvo, confira as referências e faça um trecho curto com os parâmetros de qualidade aprovados antes de iniciar a produção longa.

Para apenas trocar de Pod, **não execute `git pull`, `install.sh`, `update_nodes.sh` ou `pip install`**. Isso evita misturar migração com mudança de versão. O `start.sh` confere a instalação e inicia o servidor; não reinstala os modelos.

Se a migração envolveu cópia de arquivos ou existe suspeita de corrupção, use `bash verify.sh`. Ele não baixa pesos, mas lê arquivos grandes e pode demorar.

## 7. Se algo não funcionar

| Sintoma | Próximo passo |
|---|---|
| Pastas/modelos ausentes | Confira o ID do volume e o ponto de montagem. Não faça novo download antes disso. |
| `.venv-h3/bin/python` ausente ou link quebrado | Confira se o caminho e a imagem do container são os mesmos. O ambiente depende do Python base da imagem. |
| Python inicia, mas falta biblioteca do sistema | Compare a imagem do container com a anterior. Não apague os pesos. |
| `no kernel image`, `invalid device function` ou erro CUDA | A GPU nova pode exigir outro Torch/kernel/driver. Registre o erro; trocar de GPU não garante compatibilidade automática. |
| Nós diferentes do repositório | Confira se houve `git pull` ou mudança de arquivos durante a troca. Migração deve manter a mesma versão aprovada. |
| Porta ocupada | Confira o ComfyUI iniciado pelo template; não abra outra instalação por engano. Use as instruções do tutorial principal. |
| Falta memória | Confira GPU real, tarefas concorrentes e configuração. Rebaixar a qualidade ou reinstalar não deve ser uma ação automática. |

Um ambiente `venv` não é universalmente portátil. Reutilizá-lo exige caminhos e imagem base compatíveis. Se a nova GPU exigir outro ambiente, pode ser necessário instalar dependências compatíveis; **os modelos já guardados não precisam ser apagados**. Não é correto prometer zero reinstalação para qualquer combinação de GPU e template.

## 8. Se a instalação atual estiver no disco comum do Pod

Ela não aparecerá automaticamente em outro Pod. Será necessário **copiar uma vez** a instalação e seus dados para um Network Volume antes de seguir este roteiro. Isso pode evitar novo download dos pesos a partir do Hugging Face, mas ainda é uma transferência de dados.

Mantenha o Pod antigo até concluir a cópia e verificar a nova instalação. Não use `Terminate` como forma de pausar: o Volume Disk é apagado quando o Pod é terminado. Para esse caso, siga a [migração de arquivos documentada pelo RunPod](https://docs.runpod.io/storage/network-volumes#migrate-files-between-volumes) e preserve os caminhos, links e arquivos ocultos da instalação. Não use uma cópia com `*` se isso deixar de fora o ambiente ou metadados ocultos.

## Referências e escopo

- [RunPod: Network Volumes e conexão na criação do Pod](https://docs.runpod.io/storage/network-volumes).
- [RunPod: diferenças entre Container Disk, Volume Disk e Network Volume](https://www.runpod.io/blog/where-did-my-files-go-a-straight-guide-to-runpod-storage).
- [Python: ambientes virtuais e limites de portabilidade](https://docs.python.org/3/library/venv.html).
- [Tutorial completo e diagnóstico do H3](INSTALACAO_E_ERROS.md).

Roteiro conferido com o código do repositório e documentação dos fornecedores em 09/10/2026. A combinação específica de template/GPU do seu Pod precisa passar na verificação e no teste real. Este documento não cria, encerra ou migra Pods automaticamente.
