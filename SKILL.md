---
name: diagramacao-pge
description: Diagrama documentos institucionais da Procuradoria-Geral do Estado de Mato Grosso do Sul (PGE-MS) em PDF A4 com a identidade visual do órgão, com capa, expediente, sumário com número de página, corpo, contracapa, cabeçalho e rodapé. Use quando o usuário pedir para diagramar, formatar ou "colocar no padrão da PGE" um manual, cartilha, apostila, programa, informativo, relatório, nota técnica ou ofício, para montar capa ou contracapa, ou para transformar um .docx ou .md em publicação da PGE. Revisa ortografia e gramática antes de diagramar e refaz no padrão da PGE as tabelas e os gráficos do original, se o usuário quiser. Não gera imagens (o usuário anexa a arte da capa, se quiser) e não faz peça processual.
---

# Diagramação institucional da PGE-MS

Transforma um texto (.docx, .md ou o que o usuário colar) em PDF A4 no padrão visual da PGE-MS: Source Sans 3 no corpo, azul-marinho `#152B3F`, laranja `#F58634` só em destaque, margens de 25 mm, capa sangrada, expediente no verso, sumário com número de página calculado, contracapa e rodapé com paginação. Tudo roda no computador do usuário, em Windows ou Mac, e a skill leva consigo o design system, as fontes, o logo e os scripts.

## O que esta skill não faz

- Não gera imagem. A arte da capa vem do usuário (veja `references/capa-e-contracapa.md`); sem arte, a capa usa a faixa vetorial padrão. Gráficos de dados são outra coisa: a skill os desenha em SVG a partir de números (`grafico criar`).
- Não monta peça processual nem RTF de peticionamento.
- Não escreve o conteúdo jurídico. Diagrama o texto recebido; o texto que a skill redigir (descritor da capa, caixas de síntese) é redação nova e deve ser sinalizado ao usuário para conferência.

## Como rodar os comandos

Todo comando passa por um lançador, escrito `<dpge>` neste arquivo. No Mac e no Linux, `<dpge>` é `python3 <pasta-da-skill>/scripts/dpge.py`. No Windows, é `<pasta-da-skill>\dpge.cmd`. Rode sempre a partir da pasta de trabalho do documento, com o caminho completo do lançador, e passe os arquivos por nome relativo a ela.

Na primeira vez em cada computador, rode `<dpge> setup` (cria um ambiente próprio, instala as bibliotecas de `scripts/requirements.txt` e usa o Edge ou o Chrome do computador, ou baixa o Chromium; alguns minutos) e depois `<dpge> doctor` para conferir. O lançador só usa a biblioteca padrão e exige Python 3.10 ou mais novo. Se `setup` falhar, leia a mensagem, resolva (quase sempre falta o Python ou a rede) e rode de novo; não contorne instalando pacotes à mão.

## Fluxo

1. **Entenda o pedido e escolha o modelo.** Documento de várias páginas, com capa, expediente e sumário (manual, cartilha, apostila, programa) usa `assets/modelos/publicacao.html`. Documento curto, sem capa própria (informativo, ofício, nota técnica, relatório de poucas páginas), usa `assets/modelos/documento.html`. Na dúvida, pergunte pelo número de páginas e pela necessidade de capa.
2. **Faça as perguntas que faltam**, em linguagem simples e no máximo três por vez, com `AskUserQuestion` quando houver opções. O roteiro completo, com o que perguntar, a opção recomendada e onde cada resposta entra no modelo, está em `references/entrevista.md`. Nunca pergunte o que o texto recebido já responde.
3. **Crie uma pasta de trabalho** para o documento (ex.: `manual-xyz/`) e copie o modelo escolhido para `documento.html` dentro dela. As imagens do documento ficam ao lado do HTML. Não edite os arquivos de `assets/`.
4. **Passe o texto para HTML.** Para .docx ou .md, `<dpge> converter <arquivo> --saida corpo.html` gera o corpo e o esqueleto do sumário. Guarde uma cópia intocada do corpo (`corpo-original.html`). O conversor avisa se o original tem tabelas, imagens ou gráficos do Word.
5. **Revise ortografia e gramática** do corpo, antes de diagramar: `references/revisao.md`. Corrija só o texto, rode `<dpge> revisar corpo-original.html corpo.html --saida revisao.md`, mostre ao usuário o que mudou e os itens de ATENÇÃO, e só siga com o texto aprovado. Só se dispensa se o usuário disser que o texto já foi revisado.
6. **Tabelas e gráficos do original** (se houver): pergunte ao usuário, uma vez, se quer refazê-los no padrão institucional (recomendado) e, se sim, refaça conforme `references/graficos-e-tabelas.md` (`<dpge> grafico extrair` e `grafico criar`).
7. **Monte o documento.** Cole o corpo no modelo e monte as caixas e quadros que o texto pede, usando só os componentes de `references/componentes.md`.
8. **Prepare as imagens**, se o usuário anexou alguma: `<dpge> imagem inspecionar <arquivo>` diz o que a imagem comporta, e `imagem faixa` ou `imagem pagina` recorta sem deformar. Mostre o resultado antes de seguir.
9. **Preencha o modelo.** Capa, expediente, contracapa, metadados do cabeçalho. Nenhum marcador `[PREENCHER: ...]` pode sobrar: o build recusa o documento com eles. O texto que a skill redigir aqui (descritor, sínteses) passa pela revisão do passo 5.
10. **Confira a tipografia:** `<dpge> checar documento.html --corrigir`. Ele insere o espaço não separável depois de `art.`, `n.`, `§`, troca aspas retas por curvas e relata o resto, que se resolve à mão.
11. **Compile:** `<dpge> build documento.html --saida <Nome-do-arquivo>.pdf --conferir`. O `--conferir` grava uma imagem por página em `_conferencia/`.
12. **Acerte o sumário** (só quando há sumário): `<dpge> sumario documento.html <Nome-do-arquivo>.pdf --ate-estabilizar`. Rode de novo sempre que o texto ou as quebras de página mudarem.
13. **Olhe as páginas.** Abra as imagens de `_conferencia/`: capa, expediente, uma página de sumário, três páginas de corpo (inclusive uma com tabela, uma com gráfico e uma com caixa) e a contracapa. Procure buraco grande no pé da página, título órfão, linha terminando em `art.` ou `n.`, texto cortado, tabela sem a borda direita ou passando da margem (o build avisa: "passa N mm da margem direita"), gráfico sem rótulo e a capa fora de esquadro. Rode `<dpge> checar documento.html` de novo com o PDF pronto. Corrija e recompile. Só entregue depois de ver.
14. **Entregue** o PDF com um relatório curto: o que foi feito, o resumo da revisão de texto (e o `revisao.md`), o que a skill redigiu (para conferir), tabelas e gráficos refeitos (com os números a conferir), o que ficou pendente e o que precisa da decisão do usuário.

## Regras que não se negociam

- **Logo:** sempre o arquivo `assets/design-system/logo-pge.png`. Nunca redesenhe, recolora, estique nem peça a um modelo de imagem. Se o usuário anexar outro logo, use o dele no lugar e avise que fugiu do padrão.
- **Texto de leitura é preto**, negrito do corpo também. Cor fica na estrutura (títulos, filetes, tarjas).
- **Nada de texto dentro da imagem de capa** (acento errado, marca fora do padrão), a menos que o usuário anexe uma capa completa já aprovada, que entra sem nada por cima.
- **Não invente** norma, número de resolução, nome de autoridade, cargo, data ou estatística. O que não estiver no texto nem na resposta do usuário vira `[CONFERIR]`, e o build avisa quantos sobraram.
- **Grafia dos nomes e cargos** do expediente: confira com o usuário, com acento. É o erro que mais volta.
- **Redação nova** (descritor, síntese, rótulos) é sinalizada na entrega.
- **Revisão de texto não muda conteúdo.** Citação literal, número, norma e nome próprio ficam como estão; dúvida vira pergunta ou `[CONFERIR]`.
- **Gráfico e tabela refeitos usam só os números do original.** Nunca estime nem arredonde por conta própria.
- Para quebrar página, mexa primeiro na entrelinha (`--entrelinha`), depois no resto; nunca diminua a fonte abaixo de 10 pt. Detalhes e armadilhas em `references/build.md`.

## Onde está cada coisa

| Preciso de | Arquivo |
|---|---|
| O que perguntar e como | `references/entrevista.md` |
| Classes e marcação de cada componente | `references/componentes.md` |
| Capa, faixa de imagem, contracapa, como ajudar com a arte | `references/capa-e-contracapa.md` |
| Comandos, opções do build, quebra de página, problemas | `references/build.md` |
| Cores, fontes, margens, regras de marca | `references/identidade.md` |
| Regras de composição tipográfica e o porquê | `references/tipografia.md` |
| Revisão ortográfica e gramatical (etapa prévia) | `references/revisao.md` |
| Gráficos e tabelas do original, gerador de gráficos | `references/graficos-e-tabelas.md` |
