"""Reusable local H3 masked editing. No API, downloads or external services."""
import os
import hashlib
import torch
import torch.nn.functional as F
import folder_paths
from .logic import timing, canvas, reference_items, build_prompt
from .validation import require_finite, validate_frames

EMPTY = '(VAZIO - ignorar)'
CATEGORY = 'H3 / Reutilizavel'

def widget_string(default='', multiline=False):
    return ('STRING', {'default': default, 'multiline': multiline})

def dilate(mask, radius):
    if radius <= 0:
        return mask
    return F.max_pool2d(mask[:, None], 2 * radius + 1, stride=1, padding=radius)[:, 0]

def latent_mask(mask, samples):
    from comfy.ldm.minimax.model import FRAME_PER_TOKEN
    if samples.ndim != 5 or samples.shape[1] != 24:
        raise ValueError('Este node exige o VAE de video MiniMax H3 (24 canais).')
    _, _, t, h, w = samples.shape
    if h % 2 or w % 2:
        raise ValueError('A resolucao H3 deve ser divisivel por 32.')
    # H3 reads one mask value per 2x2 latent patch (32x32 source pixels).
    spatial = F.adaptive_max_pool2d(mask[:, None], (h // 2, w // 2))[:, 0]
    spatial = spatial.repeat_interleave(2, 1).repeat_interleave(2, 2)
    groups, pos = [], 0
    for index in range(t):
        end = pos + FRAME_PER_TOKEN[index % len(FRAME_PER_TOKEN)]
        if end > len(mask):
            raise ValueError('Frames da mascara e do VAE nao coincidem.')
        groups.append(spatial[pos:end].amax(0))
        pos = end
    if pos != len(mask):
        raise ValueError('Comprimento fora da grade temporal H3. Use H3 Preparar Video.')
    return (torch.stack(groups)[None, None] >= 0.5).float().to(samples.device)

class H3OptionalImage:
    @classmethod
    def INPUT_TYPES(cls):
        files = []
        for root, _, names in os.walk(folder_paths.get_input_directory()):
            for name in names:
                if name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')):
                    files.append(os.path.relpath(os.path.join(root, name), folder_paths.get_input_directory()).replace(os.sep, '/'))
        return {'required': {'image': ([EMPTY] + sorted(files), {'image_upload': True}),
                             'role': widget_string('Additional appearance details of the replacement person', True)}}
    RETURN_TYPES = ('H3_REF',)
    RETURN_NAMES = ('referencia_opcional',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    @classmethod
    def VALIDATE_INPUTS(cls, image, role):
        if image == EMPTY:
            return True
        return True if folder_paths.exists_annotated_filepath(image) else f'Imagem nao encontrada: {image}'
    @classmethod
    def IS_CHANGED(cls, image, role):
        if image == EMPTY:
            return EMPTY
        with open(folder_paths.get_annotated_filepath(image), 'rb') as file:
            return hashlib.sha256(file.read()).hexdigest()
    def run(self, image, role):
        if image == EMPTY:
            return ({'image': None, 'role': ''},)
        import nodes
        data = nodes.LoadImage().load_image(image)[0]
        return ({'image': data[:1], 'role': role, 'filename': image},)

class H3Brief:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {key: widget_string('', True) for key in ('target', 'action', 'preserve', 'appearance', 'protect_objects')}}
    RETURN_TYPES = ('H3_BRIEF',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, **kwargs):
        if not kwargs['target'].strip():
            raise ValueError('Descreva a pessoa alvo no campo target.')
        return (kwargs,)

class H3PrepareVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'video': ('VIDEO',), 'start_seconds': ('FLOAT', {'default': 0.0, 'min': 0, 'max': 86400, 'step': 0.01}),
                            'duration_seconds': ('FLOAT', {'default': 15.0, 'min': 0.25, 'max': 15.0, 'step': 0.01}),
                            'long_edge': ('INT', {'default': 672, 'min': 256, 'max': 1344, 'step': 32})}}
    RETURN_TYPES = ('IMAGE', 'H3_SOURCE')
    RETURN_NAMES = ('frames_H3_24fps', 'original_e_audio')
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, video, start_seconds, duration_seconds, long_edge):
        actual_duration = min(duration_seconds, float(video.get_duration()) - start_seconds)
        if actual_duration < 1 / 24:
            raise ValueError('O inicio escolhido esta fora do video.')
        count, padded_count = timing(actual_duration)
        clip = video.as_trimmed(start_seconds, count / 24, strict_duration=False)
        if clip is None:
            raise ValueError('Nao foi possivel recortar o video.')
        components = clip.get_components()
        raw = components.images[..., :3]
        fps = float(components.frame_rate)
        if len(raw) == 0 or fps <= 0:
            raise ValueError('Video vazio ou FPS invalido.')
        idx = (torch.arange(count, dtype=torch.float64) * fps / 24).floor().long().clamp(max=len(raw)-1)
        original = raw[idx].cpu()
        width, height = canvas(original.shape[2], original.shape[1], long_edge)
        frames = F.interpolate(original.movedim(-1, 1), size=(height, width), mode='bilinear', align_corners=False, antialias=True).movedim(1, -1)
        if count < padded_count:
            frames = torch.cat((frames, frames[-1:].repeat(padded_count-count, 1, 1, 1)))
        audio = components.audio
        if audio is not None:
            audio = dict(audio)
            audio['waveform'] = audio['waveform'][..., :round(count / 24 * audio['sample_rate'])]
        source = {'original': original, 'audio': audio, 'count': count, 'padded_count': padded_count,
                  'duration': count/24, 'width': width, 'height': height, 'source_fps': fps}
        return (frames, source)

class H3AutomaticMask:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'sam_model': ('MODEL',), 'sam_clip': ('CLIP',), 'brief': ('H3_BRIEF',),
                            'detection_threshold': ('FLOAT', {'default': 0.5, 'min': 0.05, 'max': 0.99, 'step': 0.01}),
                            'margin_pixels': ('INT', {'default': 12, 'min': 0, 'max': 128}),
                            'feather_pixels': ('INT', {'default': 4, 'min': 0, 'max': 32})}}
    RETURN_TYPES = ('MASK', 'MASK', 'IMAGE')
    RETURN_NAMES = ('mascara_geracao', 'mascara_composicao', 'preview_area_vermelha')
    FUNCTION = 'run'
    CATEGORY = CATEGORY + ' / Mascara v2'
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return 'h3-mask-protection-v2'

    def run(self, images, sam_model, sam_clip, brief, detection_threshold, margin_pixels, feather_pixels):
        import logging
        from comfy_extras.nodes_sam3 import SAM3_VideoTrack, SAM3_TrackToMask

        def track(text, max_objects):
            cond = sam_clip.encode_from_tokens_scheduled(sam_clip.tokenize(text))
            return SAM3_VideoTrack.execute(images, sam_model, conditioning=cond,
                        detection_threshold=detection_threshold, max_objects=max_objects,
                        detect_interval=1)[0]

        tracked = track(brief['target'], 1)
        mask = (SAM3_TrackToMask.execute(tracked, object_indices='')[0].cpu() >= 0.5).float()
        area = mask.sum(dim=(1, 2))
        visible = area > 0
        if not bool(visible.any()):
            raise ValueError('SAM3 nao encontrou a pessoa alvo. Corrija target; nenhuma geracao H3 sera feita.')

        protected = torch.zeros_like(mask)
        for label in brief['protect_objects'].splitlines():
            if not label.strip():
                continue
            data = track(label.strip(), 8)
            packed = data.get('packed_masks')
            if packed is None:
                continue
            # Native TrackToMask with an empty index merges all detections.
            # Examine each object separately: a protection query can also find
            # the target person. Do not let that duplicate turn the edit into a ring.
            for index in range(packed.shape[1]):
                candidate = (SAM3_TrackToMask.execute(data,
                    object_indices=str(index))[0].cpu() >= 0.5).float()
                overlap = (candidate * mask).sum(dim=(1, 2)) / area.clamp_min(1)
                if bool((overlap[visible] >= 0.5).any()):
                    logging.warning('[H3] Protecao %r, objeto %d, cobre a propria pessoa alvo; '
                                    'deteccao descartada. Revise a previa.', label.strip(), index)
                    continue
                protected = torch.maximum(protected, candidate)

        # A union of individually smaller mistakes must not remove most of the
        # person either. This is an overlap guard, not a semantic identity guarantee.
        retained = (mask * (1 - protected)).sum(dim=(1, 2)) / area.clamp_min(1)
        blocked = visible & (retained < 0.8)
        if bool(blocked.any()):
            frame = int(torch.nonzero(blocked, as_tuple=False)[0, 0])
            raise ValueError(f'Protecao conflitante no frame {frame}: retirou mais de 20% '
                             'da pessoa alvo. Revise protect_objects antes de gerar.')

        editing = dilate(mask, margin_pixels) * (1 - protected)
        blend = editing.clone()
        if feather_pixels:
            outer = dilate(editing, feather_pixels)
            k = 2 * feather_pixels + 1
            blend = F.avg_pool2d(outer[:, None], k, stride=1, padding=feather_pixels)[:, 0]
            blend = torch.maximum(blend, editing)
        blend *= 1 - protected
        generation = (blend > 0).float()
        overlay = images.cpu().clone()
        red = torch.tensor([1.0, 0.1, 0.1]).view(1, 1, 1, 3)
        overlay = overlay * (1 - 0.5 * generation[..., None]) + red * (0.5 * generation[..., None])
        logging.info('[H3] Mascara v2: cobertura minima do alvo %.1f%%',
                     float(retained[visible].min()) * 100)
        return (generation, blend, overlay)


class H3References:
    @classmethod
    def INPUT_TYPES(cls):
        required = {'clip': ('CLIP',), 'vae': ('VAE',), 'audio_vae': ('VAE',), 'images': ('IMAGE',),
                    'source': ('H3_SOURCE',), 'brief': ('H3_BRIEF',),
                    'ref_image_size': (['match', 'max'], {'default': 'match'})}
        required.update({f'ref_{i}': ('H3_REF',) for i in range(1, 10)})
        return {'required': required}
    RETURN_TYPES = ('CONDITIONING', 'LATENT', 'STRING')
    RETURN_NAMES = ('positive', 'latent_AV_vazio', 'prompt_final')
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, clip, vae, audio_vae, images, source, brief, ref_image_size, **kwargs):
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
        refs = reference_items([kwargs.get(f'ref_{i}') for i in range(1, 10)])
        audio = source.get('audio')
        prompt = build_prompt(brief, [r['role'] for r in refs], source['duration'], audio is not None)
        output = MiniMaxH3ReferenceToVideo.execute(clip=clip, vae=vae, audio_vae=audio_vae,
                 prompt=prompt, width=source['width'], height=source['height'], length=source['padded_count'],
                 ref_image_size=ref_image_size,
                 ref_images={f'ref_image_{i}': r['image'] for i, r in enumerate(refs)},
                 ref_videos={'ref_video_0': images},
                 ref_video_audios={'ref_video_audio_0': audio} if audio is not None else None)
        return (output[0], output[1], prompt)

class H3SourceLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'vae': ('VAE',), 'mask': ('MASK',), 'empty_av': ('LATENT',)}}
    RETURN_TYPES = ('LATENT',)
    RETURN_NAMES = ('video_original_mascarado_AV',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, images, vae, mask, empty_av):
        import comfy.nested_tensor
        samples = vae.encode(images[..., :3])
        require_finite(samples, 'Codificacao do video original pelo VAE H3')
        expected_video, audio = empty_av['samples'].unbind()
        if samples.shape != expected_video.shape:
            raise ValueError(f'VAE e Ref2VA discordam: {samples.shape} / {expected_video.shape}')
        m = latent_mask(mask, samples)
        # Native H3 denoise masks. Original encoded pixels outside the edit area.
        # Audio sampling is discarded; output always uses original source waveform.
        return ({'samples': comfy.nested_tensor.NestedTensor((samples, audio)),
                 'noise_mask': comfy.nested_tensor.NestedTensor((m, torch.ones_like(audio)))},)

class H3SafeVAEDecode:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'samples': ('LATENT',), 'vae': ('VAE',)}}
    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY

    def run(self, samples, vae):
        latent = samples['samples']
        require_finite(latent, 'Latente gerado pelo sampler H3')
        if latent.ndim != 5 or latent.shape[1] != 24:
            raise ValueError('Separe o latente de video do AV antes de decodificar (24 canais H3).')
        if getattr(vae, 'latent_channels', None) != 24:
            raise ValueError('Use o VAE de video MiniMax H3; o VAE de audio nao serve neste no.')
        images = vae.decode(latent)
        # Native video VAE returns [batch, frames, height, width, channels].
        # Match ComfyUI VAEDecode's conversion to the IMAGE frame batch.
        if images.ndim == 5:
            images = images.reshape(-1, images.shape[-3], images.shape[-2], images.shape[-1])
        validate_frames(images)
        return (images,)


class H3Composite:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'generated': ('IMAGE',), 'mask': ('MASK',), 'source': ('H3_SOURCE',)}}
    RETURN_TYPES = ('VIDEO',)
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, generated, mask, source):
        from comfy_extras.nodes_video import CreateVideo
        validate_frames(generated)
        require_finite(mask, 'Mascara de composicao')
        count = source['count']
        original = source['original']
        if len(generated) < count or len(mask) < count:
            raise ValueError('A geracao retornou menos frames que o video de origem.')
        out = composite_frames(generated[:count].cpu(), mask[:count].cpu(), original)
        return (CreateVideo.execute(images=out, fps=24.0, audio=source.get('audio'))[0],)

def composite_frames(generated, mask, original):
    size = original.shape[1:3]
    image = F.interpolate(generated.movedim(-1, 1), size=size, mode='bilinear', align_corners=False).movedim(1, -1)
    # Nearest avoids extending the edit into a protected object during upscaling.
    alpha = F.interpolate(mask[:, None], size=size, mode='nearest')[:, 0, :, :, None].clamp(0, 1)
    return original * (1-alpha) + image * alpha

NODE_CLASS_MAPPINGS = {c.__name__: c for c in (H3OptionalImage, H3Brief, H3PrepareVideo, H3AutomaticMask, H3References, H3SourceLatent, H3SafeVAEDecode, H3Composite)}
NODE_DISPLAY_NAME_MAPPINGS = {'H3OptionalImage': 'H3 Referencia opcional', 'H3Brief': 'H3 Pedido da geracao',
 'H3PrepareVideo': 'H3 Preparar video e preservar audio', 'H3AutomaticMask': 'H3 SAM3 automatico + proteger objetos',
 'H3References': 'H3 Ref2VA + prompt oficial dinamico', 'H3SourceLatent': 'H3 Latente original + mascara nativa',
 'H3Composite': 'H3 Compor sobre original + audio original',
 'H3SafeVAEDecode': 'H3 Decodificar video com protecao contra preto/NaN'}

class H3SavePrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'text': ('STRING', {'forceInput': True}),
                             'filename_prefix': widget_string('H3_REUTILIZAVEL/prompt')}}
    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, text, filename_prefix):
        import uuid
        full, name, _, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, folder_paths.get_output_directory())
        filename = f'{name}_{uuid.uuid4().hex[:10]}.txt'
        with open(os.path.join(full, filename), 'w', encoding='utf-8') as file:
            file.write(text + '\n')
        return {'ui': {'text': [text]}, 'result': ()}

NODE_CLASS_MAPPINGS['H3SavePrompt'] = H3SavePrompt
NODE_DISPLAY_NAME_MAPPINGS['H3SavePrompt'] = 'H3 Salvar prompt usado'
