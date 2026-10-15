# Gráficos e tabelas do original

Quando o documento de origem tem gráficos ou tabelas, pergunte ao usuário, uma vez, se quer que sejam **refeitos no padrão institucional** (recomendado). O `converter` avisa quando encontra tabelas, imagens ou gráficos do Word; use o aviso como gatilho. A pergunta é uma só para o documento todo, com a opção recomendada primeiro:

- **Refazer no padrão da PGE (recomendado).** Tabelas viram `table.dados` (cabeçalho marinho, linhas zebradas, números à direita, contorno fechado). Gráficos viram figuras vetoriais nas cores do design system, com título, fonte e valores no próprio gráfico.
- **Manter como estão.** Imagens do original entram como estão, em `figure.figura`. Vale só para o que já é imagem.

Duas limitações que o usuário precisa saber antes de decidir:

- Tabela feita no Word (texto) sempre é refeita, porque é a única forma de ela caber na página e quebrar entre linhas. "Manter" não se aplica a ela.
- Gráfico nativo do Word (objeto de gráfico, não imagem) não tem como ser "mantido" no PDF. Ou é refeito, ou o usuário exporta o gráfico como imagem (PNG) no Word e ela entra como figura.

## Tabelas

O `converter` já faz o essencial: a primeira linha vira cabeçalho, a classe `dados` é aplicada, colunas só de números ganham `num` (alinhadas à direita) e tabela com seis colunas ou mais ganha `densa` (corpo menor, para caber na largura útil). Depois do corpo colado, confira:

- **Largura.** O Chromium corta em silêncio o que passar da margem direita, então o build avisa ("AVISO: <table> passa N mm da margem direita"); com esse aviso na saída, o PDF está perdendo conteúdo e não pode ser entregue. Tabela larga demais: tire coluna que repete informação, abrevie o cabeçalho, ou divida em duas tabelas. Mais de oito colunas quase nunca lê bem em retrato.
- **Cabeçalho de duas linhas ou células mescladas.** O conversor não decide isso; monte à mão com `colspan` em `thead`.
- **Linha de total.** Marque com `<tr class="total">`.
- **Rótulo e fonte.** `<caption>` carrega o rótulo ("Tabela 1. Processos por área"); a fonte vai em `<p class="tab-nota">` logo abaixo.

Todo número da tabela refeita é o do original. Número ilegível ou duvidoso vira `[CONFERIR]`, nunca estimativa.

## Gráficos

Dois caminhos, conforme a origem:

**Gráfico nativo do Word.** `<dpge> grafico extrair original.docx` lê os gráficos e grava `original-graficos.json` com tipo, título, rótulos e valores (os que o Word guarda em cache), mais o parágrafo que vem antes de cada um, para saber onde colar. Confira os valores com o usuário. Tipos que o script não reproduz (dispersão, radar, bolhas, estoque) saem com aviso e são refeitos à mão ou trocados por tabela.

**Gráfico em imagem (ou em PDF colado).** Abra a imagem, leia os valores e escreva o JSON à mão. Valor que só se estima olhando a barra deve ser dito ao usuário, e o gráfico fica com `"fonte": "[CONFERIR: valores lidos da imagem do original]"` até ele confirmar. Se os números estiverem escritos na imagem, use esses.

Depois, para os dois: ajuste o JSON (título, subtítulo, fonte, unidade, casas decimais), rode `<dpge> grafico criar dados.json --saida graficos.html` e cole cada bloco no ponto do texto. A especificação e um exemplo de cada tipo estão em `assets/modelos/graficos-exemplo.json`.

### Qual tipo usar

- **barra** (horizontal): comparar categorias, sobretudo com rótulo longo. Padrão.
- **coluna**: poucos períodos ou categorias curtas; duas ou três séries lado a lado, ou `"empilhado": true` para partes de um total.
- **linha**: evolução no tempo, com cinco pontos ou mais.
- **rosca** ou **pizza**: partes de um todo, até cinco fatias. Mais que isso, use barra.
- **Mais de seis séries**: não cabe; separe em dois gráficos ou faça tabela.

O laranja é destaque, não série comum: entra como segunda série ou em `"destaque": [índice]`, para chamar a atenção para uma categoria. O gráfico escrito em `.grafico.so-completo` (barras em HTML, de `componentes.md`) é do modo completo e não é o que esta etapa usa.

### Conferência

Depois do build, olhe cada gráfico nas imagens de `_conferencia/`: números legíveis, rótulos sem corte, a legenda no lugar e o quadro inteiro na mesma página. Compare os valores com o original antes de entregar.

## Figura (imagem mantida)

Imagem sozinha num parágrafo vira `<figure class="figura"><img ...><figcaption>Legenda</figcaption></figure>`. Escreva a legenda e a fonte; sem legenda, apague o `<figcaption>`. A imagem não pode ter texto ilegível em 100% de zoom no PDF; se tiver, peça ao usuário uma versão em melhor resolução ou refaça.
