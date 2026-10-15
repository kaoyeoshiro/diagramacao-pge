# Entrevista: o que perguntar antes de diagramar

Pergunte só o que o texto recebido e o pedido não respondem. Use `AskUserQuestion` quando houver opções fechadas, no máximo três perguntas por vez, em linguagem simples, com a opção recomendada primeiro e o motivo em uma frase. Para dado que o usuário tem de digitar (nomes, endereço), peça em texto livre e junte vários em uma mensagem.

## 1. Tipo e tamanho

| Pergunta | Muda o quê |
|---|---|
| O que é o documento? (manual, cartilha, apostila, programa, informativo, ofício, relatório, nota técnica) | escolhe o modelo e o texto do cabeçalho |
| Quantas páginas, mais ou menos? Precisa de capa e sumário? | acima de umas 8 páginas ou com capa: `publicacao.html`; abaixo disso: `documento.html` |
| Vai ser lido na tela ou impresso? | na tela, nada muda; impresso, avise que a capa sangra e confira a margem com a gráfica |

## 2. Capa (publicação)

| Pergunta | Onde entra |
|---|---|
| Título completo, em até três linhas | `h1.cm-titulo`, com `<br>` nas quebras |
| Linha pequena acima do título (ex.: "Teórico e prático", "Cartilha") | `.cm-eyebrow`; pode ficar sem |
| Subtítulo ou norma de referência (ex.: Lei n. 6.490/2025) | `.cm-lei`; apague se não houver |
| Descritor de uma ou duas frases | `.cm-descritor`; se o usuário não tiver, ofereça redigir e marque como redação nova |
| Mês e ano de publicação | `.cm-data` |
| Tem arte para a capa? Veja `capa-e-contracapa.md` | faixa, página inteira ou faixa padrão |

## 3. Expediente (verso da capa)

Pergunte quem consta e em qual papel: dirigentes, autoria, revisão, diagramação, apoio, aprovação. Para cada pessoa, nome completo com acento e cargo, na ordem em que devem aparecer. Cada papel é um `.ex-bloco`. Pergunte se o crédito de diagramação é do próprio usuário e com qual cargo. Não preencha nome nem cargo de memória, nem copie de outro documento sem o usuário confirmar.

## 4. Cabeçalho e rodapé

| Pergunta | Onde entra |
|---|---|
| Qual nome curto aparece no topo de cada página? | `<meta name="vl-peca">` |
| O rodapé leva um número de referência (ofício, processo)? | `vl-processo` e `vl-rodape-rotulo`; sem eles, só a paginação |

## 5. Sumário

Pergunte se quer sumário e até que nível (partes e seções, ou só partes). O texto do corpo precisa ter título em cada nível. Se o texto de origem não tem a numeração escrita, ofereça `converter --numerar`.

## 6. Contracapa

Pergunte, com a opção "nenhuma contracapa" à vista, e depois o que entra. Cada item é opcional:

- unidade responsável, endereço, telefone, e-mail;
- site ou perfil oficial;
- como citar (referência no padrão ABNT);
- licença ou condição de reprodução do conteúdo;
- versão, data, tiragem, ISSN ou ISBN, se houver.

Item sem resposta não entra: apague o bloco do modelo em vez de deixar o marcador. A base marinho da contracapa leva sempre o nome do órgão e, se houver, o site.

## 7. Conteúdo especial

Se o texto pede quadro de modelo de documento, glossário, tabela de prazos, linha do tempo ou gráfico, confirme quais e use os componentes de `componentes.md`. Para "caixa de síntese" e "caixa de atenção", pergunte se o usuário quer que a skill proponha o texto (redação nova, a conferir) ou se ele já tem.

## 8. Revisão, tabelas e gráficos do original

Duas perguntas, só quando se aplicam:

| Pergunta | Quando | Efeito |
|---|---|---|
| O texto já passou por revisão ortográfica e gramatical? | sempre, em uma frase, sugerindo que a skill revise | sem dispensa expressa, a revisão de `revisao.md` roda e o usuário aprova o relatório |
| O original tem tabelas ou gráficos. Quer que sejam refeitos no padrão da PGE? (recomendado: sim) | o `converter` encontrou tabelas, imagens ou gráficos do Word | sim: `graficos-e-tabelas.md`; não: imagens entram como figura, e gráfico do Word precisa vir como imagem |

## 9. Fecho

Antes de compilar, repita em três linhas o que será feito (modelo, capa, o que entra no expediente e na contracapa) e só então rode o build, se o usuário não tiver dito que dispensa a conferência.
