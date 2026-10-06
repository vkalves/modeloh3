"""Launch the selected ComfyUI and validate that its workflow nodes loaded."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


def required_nodes(path):
    workflow = json.loads(Path(path).read_text())
    return {n['type'] for n in workflow['nodes']} - {'Note', 'MarkdownNote', 'Reroute', 'PrimitiveNode'}


def missing_nodes(path, available):
    return sorted(required_nodes(path) - set(available))


def main():
    root = Path(__file__).resolve().parent.parent
    directory = Path(os.environ['COMFY_DIR']).resolve()
    python = directory / '.venv-h3/bin/python'
    port = int(os.environ.get('PORT', '8188'))
    if not 1 <= port <= 65535:
        raise SystemExit('PORT deve estar entre 1 e 65535.')
    with socket.socket() as probe:
        try:
            probe.bind(('0.0.0.0', port))
        except OSError:
            print(f'ERRO: porta {port} ocupada. Pode ser o ComfyUI antigo.')
            print('Nenhum processo foi encerrado. Confira as instalacoes:')
            for proc in Path('/proc').glob('[0-9]*'):
                try:
                    args = (proc/'cmdline').read_bytes().split(b'\0')
                    if any(b'main.py' in arg for arg in args):
                        print(f'PID {proc.name}: pasta {(proc/"cwd").resolve()}')
                except (OSError, RuntimeError):
                    pass
            print('Pare a instancia antiga pelo terminal dela (Ctrl+C), depois repita start.sh.')
            print('Ou use PORT=8189 bash start.sh e exponha essa porta HTTP no RunPod.')
            return 1
    subprocess.run([str(python), '-c', 'import torch; assert torch.cuda.is_available(), "CUDA indisponivel: confira GPU, driver e Torch antes de iniciar"'], check=True)
    process = subprocess.Popen([str(python), 'main.py', '--listen', '0.0.0.0', '--port', str(port)], cwd=directory)
    try:
        deadline = time.monotonic() + 180
        info = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print(f'ERRO: servidor encerrou antes de ficar pronto (codigo {process.returncode}).')
                return process.returncode or 1
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/object_info', timeout=3) as response:
                    info = json.load(response)
                break
            except (OSError, ValueError):
                time.sleep(2)
        if info is None:
            print('ERRO: servidor nao respondeu em 180s. Confira o log de inicio.')
            return 1
        missing = missing_nodes(root/'workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json', info)
        if missing:
            print('ERRO: nos do workflow nao carregaram: ' + ', '.join(missing))
            return 1
        print(f'COMFYUI H3 PRONTO: {directory} | porta {port}', flush=True)
        print('Nos do workflow carregados. Abra a porta no RunPod e importe o workflow. Geracao ainda nao testada.', flush=True)
        print('Deixe este terminal aberto. Ctrl+C para parar.', flush=True)
        return process.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    sys.exit(main())
