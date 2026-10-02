# MiniMax H3 no RunPod — workflow SAM3 com máscara corrigida

Este repositório prepara o ComfyUI para o workflow reutilizável MiniMax H3 com substituição completa da pessoa e seleção automática da máscara SAM3 v2.

## O que é instalado

- Workflow: workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json
- Nó personalizado ComfyUI-H3-Reusable, incluindo a proteção corrigida da máscara
- Pesos H3 oficiais: Ref2VA INT8, Qwen H3 NVFP4, VAE de vídeo INT8 e VAE de áudio FP32
- Checkpoint SAM3.1 oficial usado para selecionar e proteger a pessoa e os objetos

Os pesos grandes não ficam no GitHub. O instalador baixa os arquivos públicos do Hugging Face e os coloca nas pastas esperadas pelo workflow.

## Instalar em uma instância nova

No terminal do JupyterLab:

    cd /workspace
    git clone https://github.com/vkalves/modeloh3.git
    cd modeloh3
    bash install.sh

O instalador usa ComfyUI v0.38.0, instala os pesos e o nó corrigido e copia o workflow para user/default/workflows.

Depois da instalação, reinicie o ComfyUI e abra H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json. Carregue o vídeo e as fotos de referência no workflow.

## Atualizar uma instância que já tem o repositório

    cd /workspace/modeloh3
    git pull
    bash install.sh

O instalador guarda uma cópia do nó personalizado anterior antes de substituí-lo. Ele não interrompe uma geração que já esteja em andamento; reinicie o ComfyUI depois que a fila terminar.

## Configuração inicial do workflow

O vídeo de entrada começa em 0 segundos, com duração padrão de 15 segundos e lado maior de 672 pixels na geração. O resultado é composto de volta sobre os quadros e dimensões do original e sai a 24 fps. Ajuste a duração somente se o vídeo tiver menos de 15 segundos ou se quiser testar um trecho menor.

As referências são opcionais; o workflow usa as fotos carregadas e as descrições de função de cada slot. Deixe os slots sem foto vazios.

A máscara automática seleciona a pessoa descrita em Alvo e protege os itens listados em Objetos protegidos. Confira a prévia vermelha antes de confiar no recorte, especialmente quando trocar de vídeo ou pessoa.

O áudio original é encaminhado para a montagem final quando está presente no vídeo.

## Verificar a instalação

    cd /workspace/modeloh3
    bash verify.sh

O verificador confere a versão do ComfyUI, Python/Torch/CUDA, três pesos H3 com hashes registrados, a presença do VAE de vídeo INT8 e do checkpoint SAM3.1, o nó corrigido e o workflow instalado.

O arquivo models.sha256 registra os hashes conhecidos para os pesos H3 Ref2VA, Qwen e VAE de áudio. O VAE de vídeo INT8 e o checkpoint SAM3.1 são conferidos por nome e presença após o download pelo Hugging Face Hub.
