from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import sync_nodes


class SyncTests(unittest.TestCase):
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
