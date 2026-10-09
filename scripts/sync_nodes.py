"""Stage, back up and install nodes/workflow without modifying ComfyUI or weights."""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACK = 'H3-Teste-Mascara-V1'
WORKFLOW = 'H3_PROMPT_UNICO_V2.json'
PACKAGES = ('ComfyUI-H3-Reusable', 'H3-Prompt-Unico-V2', PACK)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    source = ROOT / 'custom_nodes' / PACK
    required = ('__init__.py', 'guards.py', 'v2.py', 'base/__init__.py',
                'base/logic.py', 'base/validation.py')
    if any(not (source/name).is_file() for name in required):
        raise ValueError('Pacote validado incompleto no repositorio. Atualizacao interrompida.')
    return source, list(source.rglob('*.py'))


def check(target):
    source, files = source_files()
    for file in files:
        installed = target / 'custom_nodes' / PACK / file.relative_to(source)
        if not installed.is_file() or digest(file) != digest(installed):
            raise ValueError(f'No validado ausente ou diferente: {installed}. Execute bash update_nodes.sh e reinicie o ComfyUI.')


def ensure_stopped(target, proc_root=Path('/proc')):
    for proc in proc_root.glob('[0-9]*'):
        try:
            args = (proc/'cmdline').read_bytes().split(b'\0')
            running = any(Path(os.fsdecode(arg)).name == 'main.py' for arg in args if arg)
            if running and (proc/'cwd').resolve() == target:
                raise ValueError(f'ComfyUI deste destino esta ativo (PID {proc.name}). Pare esse servidor antes de atualizar; nenhum processo foi encerrado.')
        except (OSError, RuntimeError):
            continue


def validate_sources():
    source_files()
    for name in PACKAGES:
        package = ROOT/'custom_nodes'/name
        if not (package/'__init__.py').is_file():
            raise ValueError(f'Pacote ausente no repositorio: {name}')
        for file in package.rglob('*.py'):
            ast.parse(file.read_text(), filename=str(file))
    workflow = json.loads((ROOT/'workflows'/WORKFLOW).read_text())
    types = {n['type'] for n in workflow['nodes']}
    if not {'H3T1_H3SmartMaskV2', 'H3T1_H3ManualReferencesV2', 'H3T1_H3SafeVAEDecode'} <= types:
        raise ValueError('O workflow do repositorio nao usa os nos validados.')


def _sync_locked(target):
    ensure_stopped(target)
    validate_sources()
    backups = target/'h3_backups'
    backups.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.h3-stage-', dir=target) as staging:
        stage = Path(staging)
        entries = []
        for name in PACKAGES:
            shutil.copytree(ROOT/'custom_nodes'/name, stage/name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            entries.append((stage/name, target/'custom_nodes'/name, name))
        shutil.copy2(ROOT/'workflows'/WORKFLOW, stage/WORKFLOW)
        workflow = target/'user/default/workflows'/WORKFLOW
        workflow.parent.mkdir(parents=True, exist_ok=True)
        entries.append((stage/WORKFLOW, workflow, WORKFLOW))
        backup = Path(tempfile.mkdtemp(prefix='validated-mask-', dir=backups))
        operations = []
        try:
            for incoming, destination, name in entries:
                if destination.is_symlink():
                    raise ValueError(f'Destino e um link simbolico: {destination}. Confira o caminho antes de atualizar.')
                saved = backup/name
                old_moved = destination.exists()
                if old_moved:
                    destination.rename(saved)
                operations.append((destination, saved, old_moved))
                incoming.rename(destination)
            check(target)
            if digest(workflow) != digest(ROOT/'workflows'/WORKFLOW):
                raise ValueError('Falha ao copiar o workflow.')
        except Exception:
            for destination, saved, old_moved in reversed(operations):
                if destination.is_dir():
                    shutil.rmtree(destination)
                elif destination.exists():
                    destination.unlink()
                if old_moved:
                    saved.rename(destination)
            raise
    print(f'Nos e workflow instalados em {target}. Backup: {backup}')
    print('Reinicie o ComfyUI e reabra H3_PROMPT_UNICO_V2.json. Modelos e ComfyUI preservados.')


def sync(target):
    target = Path(target).resolve()
    if not (target/'main.py').is_file() or not (target/'custom_nodes').is_dir():
        raise ValueError(f'Destino ComfyUI invalido: {target}')
    with (ROOT/'.h3-install.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Ja existe uma instalacao ou atualizacao em andamento.') from None
        _sync_locked(target)


if __name__ == '__main__':
    import argparse
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
    except (ValueError, OSError, SyntaxError) as error:
        raise SystemExit(f'ERRO: {error}')
