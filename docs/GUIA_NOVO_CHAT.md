# Usar outro chat para preparar uma nova geração

Este guia ajuda outro chat a analisar os arquivos e criar um prompt específico para o workflow deste repositório. O processo é manual: o chat não se conecta automaticamente ao Pod e não executa a geração.

## Para você: como começar

1. Abra uma conversa nova e cole a [mensagem de início](../prompts/INICIAR_NOVO_CHAT_PT.txt).
2. Envie o **vídeo original**. Informe o trecho que quer gerar e o que quer trocar: por exemplo, apenas rosto e cabelo.
3. Espere a análise do vídeo. Depois envie as **imagens de referência**, de preferência com seus nomes e a ordem em que serão carregadas.
4. O chat analisa as referências e entrega um prompt completo para colar em **03 - PEDIDO UNIVERSAL**.
5. Confira a correspondência das fotos nos slots e use os parâmetros de qualidade que você já aprovou.

Se enviar todos os arquivos juntos, o chat deve analisar primeiro o vídeo, depois as referências, e entregar o prompt quando tiver as informações necessárias. Não é preciso reenviar arquivos que ele já conseguiu abrir.

## Instruções para o chat que receber este guia

### 1. Leia a configuração atual

Leia estes arquivos na versão atual do repositório antes de adaptar o prompt:

- [Prompt base em inglês](../prompts/BASE_CABECA_EN.txt).
- [Regras e limites do prompt](PROMPT_BASE.md).
- [Workflow atual](../workflows/H3_PROMPT_UNICO_V2.json).

Se o usuário fornecer um JSON diferente, confira-o e use a configuração realmente escolhida por ele. Não presuma que os valores do exemplo do repositório são os mesmos do Pod. Se não conseguir abrir os links, peça o conteúdo desses arquivos; não afirme que os leu.

Não reinstale ComfyUI, troque modelos, acrescente LoRA, altere a máscara ou mude resolução, passos, seed e duração para escrever um prompt. Preserve as escolhas do usuário. Os nós usam prompt manual; este guia não autoriza instalar um sistema de prompt automático.

### 2. Analise o vídeo original antes de criar o prompt

Abra o vídeo e examine o trecho solicitado ao longo do tempo, incluindo mudanças importantes, e não apenas a miniatura ou o primeiro frame. Confira o áudio quando houver ferramenta para ouvi-lo. Registre de forma breve:

- **Pessoa-alvo:** roupa original e posição que permitem distingui-la das outras pessoas.
- **Área a substituir:** exatamente o que o usuário pediu. O padrão da base é rosto e cabelo; não amplie para o corpo inteiro sem pedido.
- **Cena e câmera:** enquadramento, proporção, distância, perspectiva, movimentos, cortes e mudanças de foco observáveis.
- **Ações:** deslocamentos, orientação da cabeça, gestos, expressões visíveis e contato com objetos.
- **Ocultações:** mãos, objetos ou pessoas passando na frente da área editada; momentos em que ela sai do quadro e volta.
- **Áudio e boca:** quem fala, se a voz está fora do quadro e intervalos de fala, escuta ou outras ações da boca, quando verificáveis.
- **Preservação:** cenário, outras pessoas, corpo/roupa fora do escopo, texto e demais elementos que devem permanecer.

Use tempos somente quando medidos. Para um trecho recortado, indique os tempos relativos ao início desse trecho e, quando útil, o ponto correspondente no original. Não invente falas, movimentos, durações ou detalhes que não conseguiu observar.

Se não conseguir reproduzir o vídeo, extrair frames ou ouvir o áudio, diga qual parte ficou sem análise. Peça apenas o material necessário para resolver essa limitação, como frames de momentos importantes ou a transcrição. Não apresente uma análise completa com base apenas no nome do arquivo.

Entregue a análise em português simples, em poucos tópicos. Se as referências ainda não chegaram, peça que sejam enviadas e aguarde; não invente a nova aparência nem finalize o prompt antes delas.

Se houver várias pessoas e o alvo não estiver claro, pergunte qual deve ser alterada. Se o trecho não estiver definido, pergunte o início e a duração em uma única mensagem curta. Não escolha automaticamente 3 segundos nem trate a duração da referência como duração da geração. O workflow prepara trechos de até 15 segundos.

### 3. Analise as referências e organize seus papéis

Abra cada imagem. Identifique os ângulos, detalhes úteis de rosto e cabelo e eventuais limitações de nitidez, iluminação ou proporção. Uma folha com vários retratos é **uma imagem de entrada**, não vários slots.

Monte uma tabela curta antes do prompt:

| Arquivo enviado | Slot a carregar | Rótulo no prompt | O que deve fornecer |
|---|---|---|---|
| Nome real do arquivo | FOTO 01 | `@Image1` | Atributos observados e solicitados |
| Nome real do arquivo | FOTO 02 | `@Image2` | Atributos observados e solicitados |

A tabela acima é apenas o formato, não uma exigência de duas fotos. Use todas as referências solicitadas pelo usuário, com papéis coerentes, até o limite de nove imagens do workflow. Não ignore fotos sem explicar. Se houver conflito entre atributos ou a ordem dos arquivos não estiver clara, resolva essa dúvida antes do prompt.

Preferencialmente preencha FOTO 01, FOTO 02 etc. sem pular slots. O código numera as fotos realmente carregadas: se FOTO 02 estiver vazia e FOTO 03 tiver uma foto, esta será `@Image2`. Nunca atribua números apenas pela posição visual quando existirem slots vazios.

Para troca de cabeça, use as referências somente para os atributos de cabeça definidos pelo usuário. Não transfira automaticamente roupa, corpo, cenário, pose ou luz das fotos. Não acrescente óculos, tatuagens ou acessórios sem que façam parte do pedido e das referências apropriadas. Se o pedido for troca de corpo inteiro, adapte também as regiões editáveis e as regras de preservação para não haver contradição.

Este workflow aceita imagens e um vídeo original como referência de movimento. Não invente `@Video2` nem slots de vídeo de referência que não existem no JSON escolhido.

### 4. Adapte a base para esse caso

Parta do arquivo base; mantenha suas instruções úteis e substitua as descrições genéricas pelos fatos observados. Escreva o conteúdo do prompt em inglês. Preserve os quatro cabeçalhos externos exatamente assim:

```text
[PESSOA]
Descrição curta em inglês da pessoa no vídeo original.

[EDITAR]
Uma região por linha, coerente com o pedido.

[PROTEGER]
Somente as regiões/objetos que precisam ser protegidos.

[PROMPT]
Prompt completo adaptado, em inglês.
```

Esse bloco mostra o formato, não deve ser entregue ao usuário com esses textos de exemplo. `[PROTEGER]` pode ficar vazio quando apropriado, mas o cabeçalho deve existir. Não adicione a pessoa inteira como proteção quando ela própria é o alvo da edição.

Dentro de `[PROMPT]`, mantenha a organização da base: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape` e `non_diegetic_music`.

Adapte o conteúdo para:

- Definir cada referência e o papel de seus atributos sem contradições.
- Usar `@Video1` como autoridade de cena, câmera, ações, tempo e contexto de movimento.
- Manter a nova identidade nos diferentes ângulos, expressões, ocultações e movimento.
- Pedir pele, olhos, dentes e cabelo naturais, iluminação coerente e integração com o pescoço e o corpo originais.
- Preservar gestos, ritmo, entrada/saída do quadro, mudanças de enquadramento e ordem das ocultações que foram observados.
- Pedir movimentos de boca alinhados à fala original, respeitando pausas, falas fora do quadro e ações como comer ou beber quando realmente presentes.
- Reutilizar o áudio original quando houver; manter silêncio se a fonte não tiver áudio. Só usar `@Audio1` se confirmar que a fonte tem áudio disponível. A base evita exigir esse rótulo para também funcionar com vídeos silenciosos.

Não invente diálogo nem timecodes para reforçar sincronia labial. A área cinza da referência oculta os detalhes visuais da região editada, inclusive a boca quando selecionada. O prompt orienta o modelo; não garante reprodução perfeita desses movimentos nem corrige sozinho a sincronia labial.

### 5. Confira e entregue

Antes de responder, confira:

- Alvo e área de edição correspondem ao pedido.
- Cada rótulo citado existe, e a tabela de arquivos corresponde à numeração real.
- Nenhum trecho pede preservar o atributo que outro trecho manda substituir.
- A proteção não exclui intencionalmente toda a área que deve ser editada.
- Tempos e falas, se usados, vieram do material analisado.
- Não ficaram instruções genéricas como “describe here”, nomes de outro caso ou campos para completar dentro do prompt final.

Entregue apenas uma explicação curta, a tabela de referências e **um único bloco completo**, com as quatro seções externas, pronto para colar no campo **03 - PEDIDO UNIVERSAL**. Se o usuário pedir partes separadas, siga o formato pedido. Não diga que um resultado foi testado se a geração não foi executada.

Depois da geração, se o usuário enviar o resultado, compare com o original e as referências antes de sugerir alterações. Separe falha de aparência, movimento, sincronia labial, máscara e composição. Não atribua automaticamente todo problema ao prompt; consulte as prévias da mesma execução quando necessário.
