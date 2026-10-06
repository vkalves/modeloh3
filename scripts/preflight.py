"""Check filesystem operations Git/venv need before downloading anything."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def check_storage(parent):
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.h3-check-', dir=parent) as test:
        p = Path(test)
        f = p / 'original'
        f.write_text('H3')
        f.chmod(0o700)
        f.rename(p / 'renamed')
        (p / 'link').symlink_to(p / 'renamed')
        assert (p / 'link').read_text() == 'H3'
        subprocess.run(['git', 'init', '-q', str(p / 'repo')], check=True)
        subprocess.run(['git', '-C', str(p / 'repo'), 'config', 'core.filemode', 'false'], check=True)
    free = shutil.disk_usage(parent).free / 2**30
    print(f'Armazenamento: operacoes Git e links OK; livre informado: {free:.1f} GiB')
    if free < 5:
        raise OSError('Menos de 5 GiB livres; libere espaco antes de instalar dependencias.')
    if free > 100000:
        print('ATENCAO: capacidade virtual. Confira a capacidade real no painel do RunPod.')


if __name__ == '__main__':
    try:
        check_storage(os.environ['COMFY_DIR'])
    except (OSError, subprocess.CalledProcessError, AssertionError) as error:
        print(f'ERRO de armazenamento: {error}', file=sys.stderr)
        print('Use uma pasta de disco com suporte a chmod, links e Git. Nao repita o download neste destino.', file=sys.stderr)
        sys.exit(1)
