"""Generic MiniMax H3 masked-edit helper nodes.

This pack is designed to stay reusable across different videos and edit goals.
It does not install or replace ComfyUI, models, or the existing H3 reusable pack.
"""
import hashlib
import logging
import os
import re

import torch
import torch.nn.functional as F
import folder_paths

EMPTY = '(VAZIO - ignorar)'
CATEGORY = 'H3 / Prompt Unico V2'


def _lines(value):
    return [x.strip() for x in str(value).splitlines() if x.strip()]


def _dilate(mask, radius):
    if radius <= 0:
        return mask
    return F.max_pool2d(mask[:, None], radius * 2 + 1, stride=1, padding=radius)[:, 0]


class H3ManualBriefV2:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'pedido': ('STRING', {
            'default': (
                '[PESSOA]\n'
                'describe the target person in the source video\n\n'
                '[EDITAR]\n'
                'face\n'
                'hair\n\n'
                '[PROTEGER]\n'
                'hands\n\n'
                '[PROMPT]\n'
                'Write the complete H3 edit prompt here. Use @Video1 for the source motion/scene and @Image1, @Image2, etc. for loaded reference images.'
            ),
            'multiline': True,
        })}}

    RETURN_TYPES = ('H3_BRIEF_V2',)
    RETURN_NAMES = ('brief',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY

    def run(self, pedido):
        matches = list(re.finditer(r'^\[(PESSOA|EDITAR|PROTEGER|PROMPT)\][ \t]*$', pedido, re.M | re.I))
        sections = {}
        for i, match in enumerate(matches):
            name = match.group(1).upper()
            if name in sections:
                raise ValueError(f'Secao duplicada [{name}] no pedido.')
            begin = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(pedido)
            sections[name] = pedido[begin:end].strip()
        for key in ('PESSOA', 'EDITAR', 'PROTEGER', 'PROMPT'):
            if key not in sections:
                raise ValueError(f'Falta a secao [{key}] no pedido.')
        if not sections['PESSOA']:
            raise ValueError('Preencha [PESSOA] para localizar a pessoa correta no video.')
        if not sections['EDITAR']:
            raise ValueError('Preencha [EDITAR], uma regiao por linha (ex.: face, hair, clothing, whole person).')
        if not sections['PROMPT']:
            raise ValueError('Preencha [PROMPT] com o pedido manual para o H3.')
        return ({
            'person': sections['PESSOA'],
            'edit_regions': sections['EDITAR'],
            'protect_objects': sections['PROTEGER'],
            'prompt': sections['PROMPT'],
        },)


class H3ManualImageV2:
    @classmethod
    def INPUT_TYPES(cls):
        available = []
        input_dir = folder_paths.get_input_directory()
        for root, _, files in os.walk(input_dir):
            for name in files:
                if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')):
                    relative = os.path.relpath(os.path.join(root, name), input_dir)
                    available.append(relative.replace(os.sep, '/'))
        return {'required': {
            'image': ([EMPTY] + sorted(available), {'image_upload': True}),
            'description': ('STRING', {'default': 'image'}),
        }}

    RETURN_TYPES = ('H3_REF_V2',)
    RETURN_NAMES = ('referencia_opcional',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY

    @classmethod
    def VALIDATE_INPUTS(cls, image, description):
        if image == EMPTY:
            return True
        return True if folder_paths.exists_annotated_filepath(image) else f'Imagem nao encontrada: {image}'

    @classmethod
    def IS_CHANGED(cls, image, description):
        if image == EMPTY:
            return EMPTY
        with open(folder_paths.get_annotated_filepath(image), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run(self, image, description):
        if image == EMPTY:
            return ({'image': None},)
        import nodes
        picture = nodes.LoadImage().load_image(image)[0]
        return ({'image': picture[:1]},)


class H3SmartMaskV2:
    """Locate a person first, then segment only the requested edit regions inside that person."""
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'images': ('IMAGE',),
            'sam_model': ('MODEL',),
            'sam_clip': ('CLIP',),
            'brief': ('H3_BRIEF_V2',),
            'detection_threshold': ('FLOAT', {'default': 0.5, 'min': 0.05, 'max': 0.99, 'step': 0.01}),
            'margin_pixels': ('INT', {'default': 12, 'min': 0, 'max': 128}),
            'feather_pixels': ('INT', {'default': 4, 'min': 0, 'max': 32}),
        }}

    RETURN_TYPES = ('MASK', 'MASK', 'IMAGE')
    RETURN_NAMES = ('mascara_geracao', 'mascara_composicao', 'preview_area_vermelha')
    FUNCTION = 'run'
    CATEGORY = CATEGORY + ' / Mascara'

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return 'h3-teste-mascara-v1'

    def run(self, images, sam_model, sam_clip, brief, detection_threshold, margin_pixels, feather_pixels):
        from comfy_extras.nodes_sam3 import SAM3_VideoTrack, SAM3_TrackToMask

        def track(text, max_objects):
            cond = sam_clip.encode_from_tokens_scheduled(sam_clip.tokenize(text))
            return SAM3_VideoTrack.execute(
                images, sam_model, conditioning=cond,
                detection_threshold=detection_threshold,
                max_objects=max_objects, detect_interval=1,
            )[0]

        def merged(data):
            packed = data.get('packed_masks') if isinstance(data, dict) else None
            if packed is None:
                return torch.zeros(images.shape[0], images.shape[1], images.shape[2])
            return (SAM3_TrackToMask.execute(data, object_indices='')[0].cpu() >= 0.5).float()

        # 1) Locate the target person. This description is ONLY for identity/location.
        person = merged(track(brief['person'], 1))
        person_area = person.sum(dim=(1, 2))
        visible = person_area > 0
        if not bool(visible.any()):
            raise ValueError('SAM3 nao encontrou [PESSOA]. Ajuste apenas a descricao da pessoa alvo.')

        # 2) Segment requested parts independently, then intersect them with the target person.
        whole_terms = {
            'whole person', 'entire person', 'full person', 'full body', 'entire body',
            'whole body', 'person', 'body', 'pessoa inteira', 'corpo inteiro'
        }
        edit = torch.zeros_like(person)
        found_regions = []
        for region in _lines(brief['edit_regions']):
            key = region.lower().strip()
            if key in whole_terms:
                part = person.clone()
            else:
                part = merged(track(region, 8)) * person
            if bool((part.sum(dim=(1, 2)) > 0).any()):
                edit = torch.maximum(edit, part)
                found_regions.append(region)
            else:
                logging.warning('[H3 V2] Regiao de edicao nao encontrada: %r', region)

        if not bool((edit.sum(dim=(1, 2)) > 0).any()):
            raise ValueError('Nenhuma regiao de [EDITAR] foi encontrada dentro de [PESSOA]. Use uma regiao por linha e confira a previa.')

        # 3) Protect requested objects. Bad detections that cover most of the target person are ignored.
        protected = torch.zeros_like(person)
        for label in _lines(brief['protect_objects']):
            data = track(label, 8)
            packed = data.get('packed_masks') if isinstance(data, dict) else None
            if packed is None:
                continue
            for index in range(packed.shape[1]):
                candidate = (SAM3_TrackToMask.execute(data, object_indices=str(index))[0].cpu() >= 0.5).float()
                coverage = (candidate * person).sum(dim=(1, 2)) / person_area.clamp_min(1)
                if bool((coverage[visible] >= 0.65).any()):
                    logging.warning('[H3 V2] Protecao %r objeto %d parece ser a pessoa inteira; descartada.', label, index)
                    continue
                protected = torch.maximum(protected, candidate)

        # Do not silently continue if protection removes the entire edit.
        edit = edit * (1 - protected)
        if not bool((edit > 0).any()):
            raise ValueError('[H3 TESTE V1] A protecao removeu toda a area de edicao. '
                             'Geracao interrompida antes do H3; nenhum video original sera salvo como resultado.')
        editing = _dilate(edit, margin_pixels) * (1 - protected)
        blend = editing.clone()
        if feather_pixels:
            outer = _dilate(editing, feather_pixels)
            k = feather_pixels * 2 + 1
            blend = F.avg_pool2d(outer[:, None], k, stride=1, padding=feather_pixels)[:, 0]
            blend = torch.maximum(blend, editing)
        blend *= 1 - protected
        generation = (blend > 0).float()

        from .guards import validate_mask
        validate_mask(generation, images, 'Mascara de geracao')
        validate_mask(blend, images, 'Mascara de composicao')
        edit_area = generation.sum(dim=(1, 2))
        coverage = edit_area / person_area.clamp_min(1)
        if bool(visible.any()):
            logging.info('[H3 V2] Regioes encontradas=%s | cobertura da pessoa min=%.1f%% max=%.1f%%',
                         found_regions,
                         float(coverage[visible].min()) * 100,
                         float(coverage[visible].max()) * 100)

        overlay = images.cpu().clone()
        red = torch.tensor([1.0, 0.1, 0.1]).view(1, 1, 1, 3)
        overlay = overlay * (1 - 0.5 * generation[..., None]) + red * (0.5 * generation[..., None])
        return (generation, blend, overlay)


def normalize_references(prompt, photo_count, has_audio):
    def picture(match):
        n = int(match.group(1))
        if n < 1 or n > photo_count:
            raise ValueError(f'O prompt usa @Image{n}, mas ha somente {photo_count} fotos carregadas.')
        return f'<Picture {n}>'

    def video(match):
        n = int(match.group(1))
        if n != 1:
            raise ValueError('Este workflow possui somente @Video1 como referencia de movimento/cena.')
        return '<Video 1>'

    def audio(match):
        n = int(match.group(1))
        if n != 1 or not has_audio:
            raise ValueError('O prompt usa @Audio1, mas o video fonte nao possui audio disponivel.')
        return '<Audio 1>'

    prompt = re.sub(r'@Image(\d+)\b', picture, prompt, flags=re.I)
    prompt = re.sub(r'@Video(\d+)\b', video, prompt, flags=re.I)
    prompt = re.sub(r'@Audio(\d+)\b', audio, prompt, flags=re.I)
    return prompt


class H3ManualReferencesV2:
    """Use loaded images for identity and a sanitized source video for motion/scene.

    The editable region is neutralized in the video reference so the old identity
    does not compete with the new reference photos.
    """
    @classmethod
    def INPUT_TYPES(cls):
        required = {
            'clip': ('CLIP',), 'vae': ('VAE',), 'audio_vae': ('VAE',),
            'images': ('IMAGE',), 'source': ('H3_SOURCE',), 'brief': ('H3_BRIEF_V2',),
        }
        required.update({f'ref_{i}': ('H3_REF_V2',) for i in range(1, 10)})
        required['ref_image_size'] = (['match', 'max'], {'default': 'match'})
        required['edit_mask'] = ('MASK',)
        return {'required': required}

    RETURN_TYPES = ('CONDITIONING', 'LATENT', 'STRING', 'IMAGE')
    RETURN_NAMES = ('positive', 'latent_AV_vazio', 'prompt_final', 'referencia_movimento_sem_area_editada')
    FUNCTION = 'run'
    CATEGORY = CATEGORY

    def run(self, clip, vae, audio_vae, images, source, brief, ref_image_size, edit_mask, **kwargs):
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
        pictures = [kwargs[f'ref_{i}']['image'] for i in range(1, 10)
                    if kwargs.get(f'ref_{i}') and kwargs[f'ref_{i}'].get('image') is not None]
        if not pictures:
            raise ValueError('Carregue ao menos a FOTO 01 antes de gerar.')

        audio = source.get('audio')
        prompt = normalize_references(brief['prompt'], len(pictures), audio is not None)

        if len(edit_mask) != len(images):
            raise ValueError('Mascara e video possuem quantidades de frames diferentes.')
        from .guards import validate_mask
        validate_mask(edit_mask, images, 'Mascara recebida pelas referencias')
        m = edit_mask.to(images.device).clamp(0, 1)[..., None]
        neutral = torch.full_like(images[..., :3], 0.5)
        motion_ref = images[..., :3] * (1 - m) + neutral * m

        # Own the diagnostic tensor, independently of native model internals.
        preview = motion_ref.detach().cpu().clone()
        logging.info('[H3 TESTE V1] Referencia neutralizada: %d pixels editaveis; %d fotos.',
                     int((edit_mask > 0).sum()), len(pictures))
        output = MiniMaxH3ReferenceToVideo.execute(
            clip=clip, vae=vae, audio_vae=audio_vae,
            prompt=prompt,
            width=source['width'], height=source['height'],
            length=source['padded_count'],
            ref_image_size=ref_image_size,
            ref_images={f'ref_image_{i}': img for i, img in enumerate(pictures)},
            ref_videos={'ref_video_0': motion_ref},
            ref_video_audios={'ref_video_audio_0': audio} if audio is not None else None,
        )
        return (output[0], output[1], prompt, preview)


NODE_CLASS_MAPPINGS = {
    'H3ManualBriefV2': H3ManualBriefV2,
    'H3ManualImageV2': H3ManualImageV2,
    'H3SmartMaskV2': H3SmartMaskV2,
    'H3ManualReferencesV2': H3ManualReferencesV2,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'H3ManualBriefV2': 'H3 Pedido universal V2',
    'H3ManualImageV2': 'H3 Foto manual V2',
    'H3SmartMaskV2': 'H3 Mascara por pessoa + regioes V2',
    'H3ManualReferencesV2': 'H3 Referencias + movimento sanitizado V2',
}
