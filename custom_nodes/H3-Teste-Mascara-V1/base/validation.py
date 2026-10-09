"""Numerical checks before H3 images are composed or exported."""
import torch


def require_finite(tensor, stage):
    if not isinstance(tensor, torch.Tensor) or tensor.numel() == 0:
        raise ValueError(f'{stage}: resultado vazio ou formato invalido.')
    if not torch.isfinite(tensor).all().item():
        raise ValueError(f'{stage}: NaN/Inf detectado. Geracao interrompida antes de salvar. '
                         'Confira a instalacao/VAE e o log; veja docs/INSTALACAO_E_ERROS.md.')


def validate_frames(images):
    require_finite(images, 'Saida do VAE H3')
    if images.ndim != 4 or images.shape[-1] != 3:
        raise ValueError('Saida do VAE H3: esperado video RGB [frames, altura, largura, 3].')
    # Only an entirely black clip is rejected. Dark scenes and black cuts are valid.
    if images.abs().amax().item() <= 1e-6:
        raise ValueError('H3_VIDEO_PRETO: o VAE retornou o video inteiro preto. '
                         'Saida interrompida antes de salvar ou misturar com o original. '
                         'Execute bash verify.sh, confira o VAE INT8 e se abriu o ComfyUI correto. '
                         'Veja docs/INSTALACAO_E_ERROS.md. Um video de origem totalmente preto '
                         'tambem pode disparar esta protecao.')
