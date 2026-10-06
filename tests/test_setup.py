import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import preflight
import server


class SetupTests(unittest.TestCase):
    def test_storage_supports_git_and_cleans_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            preflight.check_storage(directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_chmod_failure_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Path, 'chmod', side_effect=PermissionError('Operation not permitted')):
                with self.assertRaises(PermissionError):
                    preflight.check_storage(directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_occupied_port_never_starts_or_kills_process(self):
        with socket.socket() as sock:
            sock.bind(('0.0.0.0', 0))
            sock.listen()
            with patch.dict(os.environ, COMFY_DIR='/tmp/h3-test', PORT=str(sock.getsockname()[1])):
                with patch.object(server.subprocess, 'Popen') as launch, patch.object(server.subprocess, 'run') as run:
                    self.assertEqual(server.main(), 1)
                    launch.assert_not_called()
                    run.assert_not_called()

    def test_missing_custom_node_detected(self):
        workflow = ROOT / 'workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json'
        available = dict.fromkeys(server.required_nodes(workflow), {})
        self.assertEqual(server.missing_nodes(workflow, available), [])
        del available['H3References']
        self.assertEqual(server.missing_nodes(workflow, available), ['H3References'])

    def test_start_uses_explicit_python_and_directory(self):
        with socket.socket() as sock:
            sock.bind(('0.0.0.0', 0))
            port = sock.getsockname()[1]
        nodes = dict.fromkeys(server.required_nodes(ROOT/'workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json'), {})
        process = MagicMock()
        process.poll.side_effect = [None, 0]
        process.wait.return_value = 0
        response = io.BytesIO(json.dumps(nodes).encode())
        with patch.dict(os.environ, COMFY_DIR='/tmp/h3-correct', PORT=str(port)):
            with patch.object(server.subprocess, 'run') as probe, patch.object(server.subprocess, 'Popen', return_value=process) as launch:
                with patch.object(server.urllib.request, 'urlopen', return_value=response):
                    self.assertEqual(server.main(), 0)
                self.assertEqual(launch.call_args.args[0][0], '/tmp/h3-correct/.venv-h3/bin/python')
                self.assertEqual(str(launch.call_args.kwargs['cwd']), '/tmp/h3-correct')
                self.assertEqual(probe.call_args.args[0][0], '/tmp/h3-correct/.venv-h3/bin/python')

    def test_failed_child_keeps_failure_exit_code(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/run_step.py'), sys.executable, '-c', 'raise SystemExit(7)'])
        self.assertEqual(result.returncode, 7)

    def test_destination_is_exported_and_python_is_isolated(self):
        env = dict(os.environ, COMFY_DIR='/tmp/h3 with spaces', VIRTUAL_ENV='/tmp/old-venv')
        result = subprocess.run(['bash', '-c', 'source "$1"; printf "%s\\n" "$PYTHON"; bash -c \'printf "%s" "$COMFY_DIR"\'', '_', str(ROOT/'scripts/common.sh')], env=env, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout, '/tmp/h3 with spaces/.venv-h3/bin/python\n/tmp/h3 with spaces')

    def test_missing_venv_does_not_fall_back_to_system_python(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(['bash', str(ROOT/'verify.sh')], env=dict(os.environ, COMFY_DIR=directory), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Ambiente H3 ausente', result.stdout)


if __name__ == '__main__':
    unittest.main()
