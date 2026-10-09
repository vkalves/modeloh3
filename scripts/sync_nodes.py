"""Copy/check repository nodes without changing ComfyUI, weights or dependencies."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACK = 'H3-Teste-Mascara-V1'
WORKFLOW = 'H3_PROMPT_UNICO_V2.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(target):
    source = ROOT / 'custom_nodes' / PACK
    for file in source.rglob('*.py'):
        installed = target / 'custom_nodes' / PACK / file.relative_to(source)
        if not installed.is_file() or digest(file) != digest(installed):
            raise ValueError(f'No validado ausente ou diferente: {installed}. Execute bash update_nodes.sh e reinicie o ComfyUI.')


def sync(target):
    if not (target / 'main.py').is_file() or not (target / 'custom_nodes').is_dir():
        raise ValueError(f'Destino ComfyUI invalido: {target}')
    backups = target / 'h3_backups'
    backups.mkdir(exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='validated-mask-', dir=backups))
    for name in ('ComfyUI-H3-Reusable', 'H3-Prompt-Unico-V2', PACK):
        destination = target / 'custom_nodes' / name
        if destination.exists():
            shutil.copytree(destination, backup / name)
        shutil.copytree(ROOT / 'custom_nodes' / name, destination,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    workflow = target / 'user/default/workflows' / WORKFLOW
    workflow.parent.mkdir(parents=True, exist_ok=True)
    if workflow.exists():
        shutil.copy2(workflow, backup / WORKFLOW)
    shutil.copy2(ROOT / 'workflows' / WORKFLOW, workflow)
    check(target)
    if digest(workflow) != digest(ROOT / 'workflows' / WORKFLOW):
        raise ValueError('Falha ao copiar o workflow.')
    print(f'Nos validados e workflow instalados em {target}. Backup: {backup}')
    print('Reinicie o ComfyUI e reabra H3_PROMPT_UNICO_V2.json. Modelos e ComfyUI preservados.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('directory')
    args = parser.parse_args()
    try:
        target = Path(args.directory).resolve()
        if args.check:
            check(target)
            print('Codigo dos nos validados confere com o repositorio.')
        else:
            sync(target)
    except (ValueError, OSError) as error:
        raise SystemExit(f'ERRO: {error}')
