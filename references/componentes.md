# Componentes

As classes vivem em `assets/design-system/componentes.css` (base) e `publicacao.css` (publicação). Use só o que o texto pede. Cada exemplo abaixo compila como está. Depois de `art.`, `n.`, `§`, `inc.`, `Lei`, `Tema`, `Súmula` e `R$`, o espaço é `&nbsp;`; o comando `checar --corrigir` insere.

## Estrutura

```html
<h2 class="secao quebra-antes">PARTE 3 &ndash; TÍTULO DA PARTE</h2>
<h3 class="subsecao">3.1. Título da seção</h3>
<p class="grupo">rótulo de grupo, em negrito:</p>
<p class="item-letra">a) item recuado de uma enumeração;</p>
```

Parte é `h2.secao`, seção é `h3.subsecao`; três níveis no máximo, dois é melhor. O título diz o argumento, não rotula ("A decisão vale para os processos em curso", não "Da vigência"). Com os números em destaque (`converter --numerar` produz esta forma):

```html
<h2 class="secao"><span class="num">1</span><span class="titulo">Título</span></h2>
<h3 class="subsecao"><span class="num">1.1</span> Título</h3>
```

Para forçar quebra de página antes de um título, `quebra-antes`; para impedir quebra dentro de um bloco, `nao-quebrar`; para colar dois blocos, `juntar`. O primeiro título depois do sumário leva `primeira`.

## Caixas

```html
<div class="sintese"><div class="sintese-rotulo">Em síntese</div><p>…</p></div>

<div class="atencao"><div class="atencao-marca">!</div><div><p>…</p></div></div>

<div class="exemplo"><p>Exemplo: …</p></div>

<div class="nota"><p><span class="n-rot">Nota explicativa 1:</span> …</p></div>
```

`sintese` é o que o leitor leva da seção; `atencao` é o ponto em que mais se erra (laranja, use pouco); `exemplo` é o caso prático, mais leve que a síntese; `nota` é a observação em cinza, dentro de modelo de documento. Caixa (`sintese` ou `exemplo`) com três ou mais parágrafos vai com `pode-quebrar` (`<div class="sintese pode-quebrar">`), senão abre vão no pé da página.

## Tabelas

```html
<table class="dados">
  <caption>Título da tabela</caption>
  <thead><tr><th>Coluna</th><th class="num">Valor</th></tr></thead>
  <tbody><tr><td>Item</td><td class="num">12</td></tr></tbody>
</table>
<p class="tab-nota">Fonte e observação.</p>
```

Tabela longa leva `class="dados pode-quebrar"`: parte entre linhas, repete o cabeçalho e cada linha é indivisível. Coluna numérica: `class="num"` alinha à direita. Tabela de critérios (comparação de requisitos) é `table.criterios`.

## Glossário, quadro de requisitos, confronto

```html
<dl class="glossario">
  <div><dt>Termo</dt><dd>Definição.</dd></div>
</dl>

<div class="requisitos">
  <div><span class="r-rotulo">Rótulo</span><span class="r-texto">Texto</span></div>
  <div><span class="r-rotulo">Rótulo</span><span class="r-texto">Texto</span></div>
</div>

<div class="confronto">
  <div><span class="c-rotulo">Texto original</span><span class="c-texto">…</span></div>
  <div class="divergente"><span class="c-rotulo">Texto sancionado</span><span class="c-texto">…</span></div>
</div>
```

`requisitos` são quatro células em duas colunas. `confronto` compara duas redações; a linha com `divergente` ganha o fundo de destaque.

## Modelos de documento (para o leitor copiar)

```html
<ol class="indice-modelos"><li>Termo de abertura</li><li>Termo de juntada</li></ol>

<div class="modelo">
  <div class="modelo-cab"><span class="m-num">01</span><span class="m-nome">Termo de abertura</span></div>
  <div class="modelo-corpo">
    <p><span class="m-item">Art.&nbsp;1º</span> Texto com <span class="campo">(campo a preencher)</span>.</p>
    <p>Data: <span class="linha"></span> &nbsp; <span class="caixa"></span> marcar</p>
    <div class="fecho-modelo"><span class="campo">(local e data)</span><span class="campo">(assinatura)</span></div>
  </div>
</div>
```

O modelo parte entre páginas. `.campo` é o que o leitor preenche, em laranja; `.linha` e `.caixa` são o traço e o quadradinho de formulário. Explique a convenção do laranja na abertura da seção.

## Sumário

```html
<div class="sumario"><ol>
  <li class="parte"><span class="s-num">1</span><span class="s-tit"><span>PRIMEIRA PARTE</span></span><span class="s-pag">&mdash;</span></li>
  <li class="sub"><span class="s-num">1.1</span><span class="s-tit"><span>Primeira seção</span></span><span class="s-pag">&mdash;</span></li>
</ol></div>
```

O texto de cada `s-tit` tem de ser igual ao título no corpo (o sumário é casado pelo texto). `<dpge> sumario` troca o traço pelo número de página.

## Notas de rodapé

```html
<p>O prazo é de quinze dias<span class="nota-rodape">Art.&nbsp;183 do CPC.</span> contados da intimação.</p>
```

A nota desce para o pé da página em que a chamada aparece, numerada por ordem. `nota` (caixa no fluxo) e `nota-rodape` (rodapé) são coisas diferentes. Não combina com capa própria: o build recusa a combinação, então use nota de rodapé só em documento curto, ou troque por texto no corpo.

## Documento curto (informativo, ofício, relatório)

```html
<div class="doc-abertura">
  <div class="doc-eyebrow">Linha pequena</div>
  <h1 class="doc-titulo">Título,<br>em duas linhas</h1>
  <div class="doc-periodo">Julho de 2026</div>
</div>
<dl class="ficha"><dt>Período</dt><dd>Julho de 2026</dd></dl>
<div class="enderecamento">Ao Senhor Fulano de Tal</div>     <!-- ofício: no lugar da abertura -->
<div class="fecho"><p>Campo Grande, 15 de outubro de 2026.</p></div>
<div class="assinatura">
  <img class="rubrica" src="rubrica.png" alt="">  <!-- opcional, do próprio signatário -->
  <div class="filete"></div><div class="nome">Nome</div><div class="cargo">Cargo</div>
</div>
```

## Números-chave, linha do tempo e gráfico (modo completo)

Estes blocos só aparecem com `--modo completo` (classe `so-completo`); no modo sóbrio somem. Quando a informação precisa existir nos dois, escreva um bloco `so-completo` e outro `so-sobrio`.

```html
<div class="numeros so-completo">
  <div><span class="n-valor">4</span><span class="n-rotulo">frentes de melhoria</span></div>
</div>

<div class="timeline so-completo">
  <div class="timeline-rotulo">Cronologia</div>
  <ol>
    <li class="marco"><span class="tl-titulo">Marco</span><span class="tl-texto">O que aconteceu.</span></li>
    <li><span class="tl-titulo">Etapa</span><span class="tl-texto">O que aconteceu.</span></li>
  </ol>
</div>

<div class="grafico so-completo">
  <div class="grafico-titulo">Título do gráfico</div>
  <div class="grafico-sub">Fonte do dado.</div>
  <div class="barra-linha"><span class="barra-rotulo">Rótulo</span>
    <div class="barra-trilho"><div class="barra" style="width:112mm"></div><span class="barra-valor">120</span></div></div>
</div>
```

Largura da barra em mm, 112 mm para a maior e as outras em proporção. Todo número de capa, tabela ou gráfico tem de constar do próprio documento: gráfico não é lugar de estimativa nova.

## Componentes herdados de peça processual

`tese`, `precedente`, `pedidos`, `fecho` de petição e as capas `.capa-tarja` existem no CSS por herança. Fora do escopo desta skill; não os use em publicação.

## Tabela larga, gráfico em SVG e figura

- `table.dados.densa`: corpo e respiro menores, para tabela de seis colunas ou mais (o `converter` aplica sozinho). Qualquer tabela tem contorno nos quatro lados e a célula quebra palavra sem ponto de quebra (número de processo, URL), então nada passa da margem direita. Tabela que ainda assim ficar ilegível: menos colunas, ou duas tabelas.
- `<div class="grafico">` com `<svg class="grafico-svg">`: gerado por `grafico criar` (veja `graficos-e-tabelas.md`); título em `.grafico-titulo`, subtítulo em `.grafico-sub`, fonte em `.grafico-fonte`. Aparece em qualquer modo (não leva `so-completo`).
- `<figure class="figura"><img src="..." alt="..."><figcaption>Legenda. Fonte: ...</figcaption></figure>`: imagem do original mantida. Não parte entre páginas.
