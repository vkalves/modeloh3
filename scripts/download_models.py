"""Resolve model revisions, check free space and resume Hugging Face downloads."""
import os
from pathlib import Path
import shutil
from huggingface_hub import HfApi, hf_hub_download, hf_hub_url, get_hf_file_metadata

FILES = [
    ('Comfy-Org/MiniMax-H3', 'diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors'),
    ('Comfy-Org/MiniMax-H3', 'text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'),
    ('Comfy-Org/MiniMax-H3', 'vae/minimax_h3_video_vae_int8_convrot.safetensors'),
    ('Comfy-Org/MiniMax-H3', 'vae/minimax_h3_audio_vae_fp32.safetensors'),
    ('Comfy-Org/sam3.1', 'checkpoints/sam3.1_multiplex_fp16.safetensors'),
]

if __name__ == '__main__':
    token = os.environ.get('HF_TOKEN') or None
    api = HfApi(token=token)
    revisions = {repo: api.model_info(repo).sha for repo in dict(FILES)}
    planned = []
    for repo, name in FILES:
        revision = revisions[repo]
        meta = get_hf_file_metadata(hf_hub_url(repo, name, revision=revision), token=token)
        if not meta.size:
            raise RuntimeError(f'Tamanho indisponivel: {name}; download nao iniciado.')
        planned.append((repo, name, revision, meta.size))
    # Conservative: changed/incomplete files may coexist with their replacements.
    needed = sum(size for _, name, _, size in planned
                 if not (Path('models') / name).is_file() or (Path('models') / name).stat().st_size != size)
    if shutil.disk_usage('models').free < needed + 5 * 2**30:
        raise RuntimeError(f'Espaco insuficiente: reserve pelo menos {needed / 2**30 + 5:.1f} GiB livres para pesos e margem.')
    for index, (repo, name, revision, size) in enumerate(planned, 1):
        print(f'[{index}/{len(planned)}] {name} ({size/2**30:.2f} GiB)', flush=True)
        hf_hub_download(repo_id=repo, filename=name, revision=revision, local_dir='models', token=token)
    print('Downloads concluidos. A verificacao de integridade vem a seguir.', flush=True)
