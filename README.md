# MiniMax H3 no RunPod

Instalador para recriar o ambiente MiniMax H3 usado no ComfyUI sem baixar cada arquivo manualmente.

## Ambiente alvo

- RunPod
- Template recomendado: **ComfyUI - CUDA 13.0**
- Volume persistente montado em `/workspace`
- ComfyUI fixado em **v0.38.0**
- Modelos oficiais de `Comfy-Org/MiniMax-H3`

## Modelos instalados

- `minimax_h3_ref2va_pruned_int8_convrot.safetensors`
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`
- `minimax_h3_video_vae_fp16.safetensors`
- `minimax_h3_audio_vae_fp32.safetensors`

Os arquivos grandes **nao ficam armazenados no GitHub**. O script baixa diretamente do Hugging Face e depois confere o SHA256.

## Workflow incluido

O repositorio tambem inclui:

`workflows/H3_FINAL_RTX_PRO_6000_REVISADO.json`

Durante a instalacao, ele e copiado automaticamente para:

`/workspace/runpod-slim/ComfyUI/user/default/workflows/`

Assim o workflow final ja aparece no ComfyUI depois da instalacao.

## Instalacao em uma conta nova do RunPod

Abra **JupyterLab > Terminal** e rode:

```bash
cd /workspace
git clone https://github.com/vkalves/modeloh3.git
cd modeloh3
bash install.sh
```

Depois disso, aguarde os downloads. O script pode ser executado novamente: arquivos ja presentes no cache/local nao precisam ser baixados do zero.

## Se o repositorio ja foi clonado

```bash
cd /workspace/modeloh3
git pull
bash install.sh
```

## Apenas verificar a instalacao

```bash
cd /workspace/modeloh3
bash verify.sh
```

O verificador confere:

- versao do ComfyUI
- dependencias Python com `pip check`
- Torch / CUDA / GPU
- SHA256 dos quatro modelos

## Caminho padrao

O instalador espera o ComfyUI em:

```text
/workspace/runpod-slim/ComfyUI
```

Se outro template usar um caminho diferente:

```bash
COMFY_DIR=/workspace/ComfyUI bash install.sh
```

## Hugging Face

Os modelos usados sao publicos, entao normalmente nao e necessario token.

Se algum dia for necessario:

```bash
export HF_TOKEN="SEU_TOKEN"
bash install.sh
```

Nao salve tokens ou senhas neste repositorio.

## Observacao sobre GPU

O encoder Qwen usado aqui e NVFP4. GPUs Blackwell sao as mais adequadas para esse formato. Para geracoes finais pesadas, use uma GPU com bastante VRAM e RAM do Pod.

## Versoes fixadas

As versoes foram fixadas para reproduzir o ambiente validado:

- ComfyUI `v0.38.0`
- `comfyui-frontend-package 1.53.6`
- `comfyui-workflow-templates 0.11.70`
- `comfyui-embedded-docs 0.5.12`
- `comfy-kitchen 0.2.36`
- `comfy-aimdo 0.5.5`
