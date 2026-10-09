from pathlib import Path
import sys
import tempfile
import unittest
import fcntl
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import sync_nodes


class SyncTests(unittest.TestCase):
    def make_target(self, tmp):
        target=Path(tmp)
        (target/'main.py').write_text('original server')
        (target/'custom_nodes').mkdir()
        return target

    def test_missing_repository_pack_does_not_pass_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sync_nodes, 'ROOT', Path(tmp)):
                with self.assertRaisesRegex(ValueError, 'incompleto'):
                    sync_nodes.check(Path(tmp))

    def test_running_target_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'ComfyUI';target.mkdir()
            proc=Path(tmp)/'proc/123';proc.mkdir(parents=True)
            (proc/'cmdline').write_bytes(b'python\0/workspace/ComfyUI/main.py\0')
            (proc/'cwd').symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'esta ativo'):
                sync_nodes.ensure_stopped(target, Path(tmp)/'proc')
            sync_nodes.ensure_stopped(Path(tmp)/'other', Path(tmp)/'proc')

    def test_install_lock_prevents_concurrent_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.make_target(tmp)
            with (sync_nodes.ROOT/'.h3-install.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError, 'andamento'):
                    sync_nodes.sync(target)
            self.assertEqual(list((target/'custom_nodes').iterdir()), [])

    def test_failed_staging_does_not_touch_old_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.make_target(tmp)
            old=target/'custom_nodes'/sync_nodes.PACK;old.mkdir()
            (old/'keep').write_text('old')
            with patch.object(sync_nodes.shutil, 'copytree', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    sync_nodes.sync(target)
            self.assertEqual((old/'keep').read_text(), 'old')

    def test_failed_commit_restores_all_previous_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=self.make_target(tmp)
            for name in sync_nodes.PACKAGES:
                old=target/'custom_nodes'/name;old.mkdir();(old/'keep').write_text(name)
            flow=target/'user/default/workflows'/sync_nodes.WORKFLOW
            flow.parent.mkdir(parents=True);flow.write_text('old workflow')
            original_rename=Path.rename
            def fail_last_stage(path, destination):
                if path.name==sync_nodes.WORKFLOW and path.parent.name.startswith('.h3-stage-'):
                    raise OSError('simulated install failure')
                return original_rename(path, destination)
            with patch.object(Path, 'rename', fail_last_stage):
                with self.assertRaisesRegex(OSError, 'simulated'):
                    sync_nodes.sync(target)
            for name in sync_nodes.PACKAGES:
                self.assertEqual((target/'custom_nodes'/name/'keep').read_text(), name)
            self.assertEqual(flow.read_text(), 'old workflow')

    def test_update_preserves_models_and_backs_up_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target/'main.py').write_text('original server')
            (target/'custom_nodes').mkdir()
            (target/'models').mkdir()
            (target/'models/keep').write_text('weights')
            flow=target/'user/default/workflows/H3_PROMPT_UNICO_V2.json'
            flow.parent.mkdir(parents=True)
            flow.write_text('user settings')
            sync_nodes.sync(target)
            sync_nodes.check(target)
            self.assertEqual((target/'main.py').read_text(),'original server')
            self.assertEqual((target/'models/keep').read_text(),'weights')
            saved=list((target/'h3_backups').glob('*/H3_PROMPT_UNICO_V2.json'))
            self.assertEqual(saved[0].read_text(),'user settings')
            (target/'custom_nodes'/sync_nodes.PACK/'guards.py').write_text('old code')
            with self.assertRaisesRegex(ValueError,'diferente'):
                sync_nodes.check(target)


if __name__=='__main__':
    unittest.main()
