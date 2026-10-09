"""Check the actual installed sources, not only the version label (no GPU imports)."""
import ast
import os
from pathlib import Path
import sys


def check_compatibility(directory):
    directory = Path(directory)
    try:
        loader = ast.parse((directory / 'comfy/sd.py').read_text())
        vae = ast.parse((directory / 'comfy/ldm/minimax/vae.py').read_text())
    except (OSError, SyntaxError) as error:
        raise ValueError(f'Fontes do ComfyUI ausentes ou invalidas: {error}') from error
    supported = False
    for branch in ast.walk(loader):
        if not isinstance(branch, ast.If):
            continue
        # Inspect only this branch body, excluding unrelated elif branches.
        body = ast.Module(body=branch.body, type_ignores=[])
        calls = [n for n in ast.walk(body) if isinstance(n, ast.Call)]
        constructors = [n for n in calls if isinstance(n.func, ast.Attribute)
                        and n.func.attr == 'MiniMaxH3VideoVAE']
        if constructors:
            names = {n.func.attr for n in calls if isinstance(n.func, ast.Attribute)}
            supported = ('detect_layer_quantization' in names and 'mixed_precision_ops' in names
                         and any(k.arg == 'operations' for n in constructors for k in n.keywords))
            if supported:
                break
    classes = [n for n in ast.walk(vae) if isinstance(n, ast.ClassDef) and n.name == 'MiniMaxH3VideoVAE']
    decoder_support = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                          and n.func.id == 'ViT3DDecoder'
                          and any(k.arg == 'operations' for k in n.keywords)
                          for cls in classes for n in ast.walk(cls))
    if not supported or not decoder_support:
        raise ValueError('ComfyUI sem suporte ao VAE H3 INT8/convrot. '
                         'Pare o servidor e execute bash install.sh neste repositorio. '
                         'Nao tente corrigir isso mudando o prompt ou a mascara.')
    return 'Suporte VAE H3 INT8/convrot encontrado nas fontes instaladas.'


if __name__ == '__main__':
    try:
        print(check_compatibility(os.environ['COMFY_DIR']))
    except (ValueError, KeyError) as error:
        print(f'ERRO: {error}', file=sys.stderr)
        sys.exit(1)
