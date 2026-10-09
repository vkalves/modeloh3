# Prompt base para novas gerações

O prompt já está no campo **03 - PEDIDO UNIVERSAL** do workflow atualizado. Também está disponível em [BASE_CABECA_EN.txt](../prompts/BASE_CABECA_EN.txt).

Quer que outro chat faça a análise e a adaptação para você? Siga o [guia para novas gerações em outro chat](GUIA_NOVO_CHAT.md).

## Como usar

1. Em `[PESSOA]`, substitua a frase de exemplo por uma descrição curta da pessoa **no vídeo original**: roupa e posição no quadro. Exemplo: `the seated woman wearing the brown dress on the purple bench`.
2. Carregue a referência da nova cabeça em **FOTO 01**. A base usa apenas `@Image1`, para funcionar também com uma única foto.
3. Se usar outras fotos, acrescente seus papéis em `subject_definitions` e `retention_analysis`, conforme o exemplo abaixo. Cite somente fotos carregadas; os slots vazios são ignorados na numeração.
4. Mantenha `[EDITAR] face / hair` para trocar somente rosto e cabelo. Essa base não solicita troca de corpo ou roupa. Para outra área, ajuste tanto `[EDITAR]` quanto o texto que descreve o que deve ser substituído/preservado.
5. Use resolução, passos e demais parâmetros que você já aprovou. Este prompt não muda esses valores.

O prompt continua manual. Ele pede realismo, fidelidade de identidade, câmera e movimentos consistentes com o vídeo original e boca alinhada à fala original.

## Exemplo de papéis com três referências

Se as fotos mostram, respectivamente, frente/3-4, perfis do cabelo e detalhes faciais, substitua a descrição de `<Subject 2>` em `subject_definitions` por:

```text
<Subject 2> is the same replacement identity shown in @Image1, @Image2 and @Image3. @Image1 defines the front and three-quarter facial identity. @Image2 defines the side profile, hairline, hairstyle and hair shape. @Image3 defines fine facial details. Transfer only these assigned head attributes; retain the source body, clothing and scene.
```

Em `retention_analysis`, substitua a linha de `@Image1` por estas três linhas:

```text
@Image1: attribute_transfer - front and three-quarter facial identity and facial proportions.
@Image2: attribute_transfer - side profile and the same identity's hairline, hairstyle and hair shape.
@Image3: attribute_transfer - fine facial identity details, including eyes, nose, mouth and natural skin texture.
```

Adapte os papéis ao conteúdo real das suas fotos. Fotografias de pessoas diferentes ou atributos contraditórios podem prejudicar a identidade.

## Limites para avaliar o resultado

- O workflow reaproveita o áudio original, mas isso **não é um corretor de sincronia labial**. A boca é gerada pelo H3; precisa ser conferida no resultado.
- A área selecionada fica cinza na referência de movimento. Ao cobrir toda a cabeça, ela também oculta da referência visual os movimentos originais da boca e detalhes da expressão. O modelo recebe o áudio quando disponível e o contexto restante, mas o prompt não recupera informação visual ocultada.
- O pipeline trabalha a 24 fps. Preserva a duração do trecho dentro dessa grade; não conserva todos os frames de uma fonte com outra taxa.
- Fundo e regiões externas à máscara vêm dos frames originais na composição. Isso não garante identidade ou movimentos perfeitos dentro da área gerada, nem cópia byte a byte após a compressão do MP4.
- Não adicione falas inventadas ou tempos inventados ao prompt. Se detalhar falas ou momentos, use apenas o conteúdo e os tempos reais do trecho.

Referência de estrutura: [guia oficial de prompts do ComfyUI para H3](https://github.com/Comfy-Org/docs/blob/main/tutorials/video/minimax/minimax-h3-prompt-guide.mdx). As seções e os papéis orientam o modelo; não garantem fidelidade absoluta.
