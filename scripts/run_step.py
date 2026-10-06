"""Run a command with periodic activity messages, preserving its exit code."""
import subprocess
import sys
import time

if __name__ == '__main__':
    process = subprocess.Popen(sys.argv[1:])
    start = time.monotonic()
    try:
        while True:
            try:
                sys.exit(process.wait(timeout=20))
            except subprocess.TimeoutExpired:
                print(f'[ativo ha {int(time.monotonic()-start)}s] Processo ainda executando; isso nao comprova progresso. Log acima.', flush=True)
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        sys.exit(130)
