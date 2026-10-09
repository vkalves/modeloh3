import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_compatibility import check_compatibility


class CompatibilityTests(unittest.TestCase):
    def fixture(self, directory, quantized=True, decoder=True):
        root = Path(directory)
        (root / 'comfy/ldm/minimax').mkdir(parents=True)
        quant = 'q = utils.detect_layer_quantization(sd, "")\n    ops = ops_module.mixed_precision_ops(q, dtype)\n    ' if quantized else ''
        (root / 'comfy/sd.py').write_text('if "h3" in sd:\n    ' + quant + 'vae = mod.MiniMaxH3VideoVAE(operations=ops)\n')
        (root / 'comfy/ldm/minimax/vae.py').write_text('class MiniMaxH3VideoVAE:\n    def __init__(self, operations=None):\n        self.decoder = ViT3DDecoder(' + ('operations=operations' if decoder else '') + ')\n')

    def test_loader_and_decoder_must_both_support_quantization(self):
        import tempfile
        for quantized, decoder, accepted in [(True, True, True), (False, True, False), (True, False, False)]:
            with self.subTest(quantized=quantized, decoder=decoder), tempfile.TemporaryDirectory() as directory:
                self.fixture(directory, quantized, decoder)
                if accepted:
                    self.assertIn('INT8', check_compatibility(directory))
                else:
                    with self.assertRaisesRegex(ValueError, 'INT8'):
                        check_compatibility(directory)

    def test_missing_sources_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'ausentes'):
                check_compatibility(directory)


# Load the real custom nodes without importing an entire ComfyUI installation.
spec = importlib.util.spec_from_file_location('h3_test_nodes', ROOT / 'custom_nodes/ComfyUI-H3-Reusable/__init__.py', submodule_search_locations=[str(ROOT / 'custom_nodes/ComfyUI-H3-Reusable')])
nodes = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nodes
with patch.dict(sys.modules, folder_paths=types.ModuleType('folder_paths')):
    spec.loader.exec_module(nodes)


class DecodeTests(unittest.TestCase):
    def test_native_five_dimensional_video_output_flattened(self):
        vae = MagicMock(latent_channels=24)
        images = torch.arange(1, 1 + 2 * 3 * 8 * 8 * 3, dtype=torch.float32).reshape(2, 3, 8, 8, 3)
        vae.decode.return_value = images
        result = nodes.H3SafeVAEDecode().run({'samples': torch.ones(2, 24, 2, 2, 2)}, vae)[0]
        self.assertEqual(result.shape, (6, 8, 8, 3))
        self.assertTrue(torch.equal(result, images.reshape(6, 8, 8, 3)))

    def test_black_clip_rejected(self):
        vae = MagicMock(latent_channels=24)
        vae.decode.return_value = torch.zeros(2, 8, 8, 3)
        with self.assertRaisesRegex(ValueError, 'H3_VIDEO_PRETO'):
            nodes.H3SafeVAEDecode().run({'samples': torch.ones(1, 24, 2, 2, 2)}, vae)

    def test_nonfinite_latent_rejected_before_decode(self):
        for value in [float('nan'), float('inf')]:
            vae = MagicMock(latent_channels=24)
            with self.assertRaisesRegex(ValueError, 'NaN/Inf'):
                nodes.H3SafeVAEDecode().run({'samples': torch.full((1, 24, 2, 2, 2), value)}, vae)
            vae.decode.assert_not_called()

    def test_nonfinite_decoded_output_rejected(self):
        vae = MagicMock(latent_channels=24)
        vae.decode.return_value = torch.full((2, 8, 8, 3), float('nan'))
        with self.assertRaisesRegex(ValueError, 'NaN/Inf'):
            nodes.H3SafeVAEDecode().run({'samples': torch.ones(1, 24, 2, 2, 2)}, vae)

    def test_dark_scene_and_black_cut_accepted(self):
        vae = MagicMock(latent_channels=24)
        images = torch.full((2, 8, 8, 3), 0.001)
        images[0] = 0
        vae.decode.return_value = images
        result = nodes.H3SafeVAEDecode().run({'samples': torch.ones(1, 24, 2, 2, 2)}, vae)
        self.assertIs(result[0], images)

    def test_audio_vae_cannot_decode_video(self):
        vae = MagicMock(latent_channels=8)
        with self.assertRaisesRegex(ValueError, 'VAE de video'):
            nodes.H3SafeVAEDecode().run({'samples': torch.ones(1, 24, 2, 2, 2)}, vae)
        vae.decode.assert_not_called()

    def test_composition_does_not_hide_black_generation(self):
        video_module = types.ModuleType('comfy_extras.nodes_video')
        video_module.CreateVideo = MagicMock()
        with patch.dict(sys.modules, {'comfy_extras': types.ModuleType('comfy_extras'), 'comfy_extras.nodes_video': video_module}):
            with self.assertRaisesRegex(ValueError, 'H3_VIDEO_PRETO'):
                nodes.H3Composite().run(torch.zeros(2, 8, 8, 3), torch.ones(2, 8, 8), {})
        video_module.CreateVideo.execute.assert_not_called()

    def test_workflow_both_outputs_use_guarded_decoder(self):
        workflow = json.loads((ROOT / 'workflows/H3_PROMPT_UNICO_V2.json').read_text())
        decoder = next(n for n in workflow['nodes'] if n['type'] == 'H3SafeVAEDecode')
        self.assertFalse(any(n['type'] == 'VAEDecode' for n in workflow['nodes']))
        for target_type in ['H3Composite', 'CreateVideo']:
            targets = {n['id'] for n in workflow['nodes'] if n['type'] == target_type}
            self.assertTrue(any(link[1] == decoder['id'] and link[3] in targets for link in workflow['links']))


if __name__ == '__main__':
    unittest.main()
