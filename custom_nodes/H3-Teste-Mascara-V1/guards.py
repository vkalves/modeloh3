import logging
import torch


def validate_mask(mask, images, label):
    if mask.ndim != 3 or tuple(mask.shape) != tuple(images.shape[:3]):
        raise ValueError(f'[H3 TESTE V1] {label}: tamanho diferente dos frames.')
    if not bool(torch.isfinite(mask).all()):
        raise ValueError(f'[H3 TESTE V1] {label}: valores NaN/Inf.')
    if bool(((mask < 0) | (mask > 1)).any()):
        raise ValueError(f'[H3 TESTE V1] {label}: valores fora de 0 a 1.')
    active = (mask > 0).flatten(1).any(1)
    if not bool(active.any()):
        raise ValueError(f'[H3 TESTE V1] {label}: vazia em todos os frames. Geracao bloqueada.')
    # Individual empty frames can be legitimate when the target leaves the shot
    # or is fully occluded. Never remove real protections to force an edit.
    logging.info('[H3 TESTE V1] %s: %d/%d frames com edicao.',
                 label, int(active.sum()), len(active))
