# Compilar, conferir e resolver problemas

Todos os comandos passam pelo lançador `<dpge>`, que roda de qualquer pasta:

```bash
python3 <pasta-da-skill>/scripts/dpge.py <comando> ...      # Mac e Linux
<pasta-da-skill>\dpge.cmd <comando> ...                     # Windows
```

No Windows o `dpge.cmd` acha o Python (`py` ou `python`) sozinho.

## Comandos

| Comando | O que faz |
|---|---|
| `setup` | cria o ambiente, instala as bibliotecas e confere o navegador (uma vez); baixa o Chromium só se não houver Edge nem Chrome. `--forcar` refaz do zero |
| `doctor` | confere Python, ambiente, fontes, logo e CSS |
| `build doc.html` | compila em PDF A4. Opções abaixo |
| `sumario doc.html [pdf] --ate-estabilizar` | compila, lê o PDF e grava os números de página no sumário, repetindo até estabilizar |
| `checar doc.html [--corrigir]` | relata (e corrige o que é mecânico) problemas de tipografia |
| `converter arq.docx\|.md` | gera o corpo em HTML e o esqueleto do sumário |
| `imagem inspecionar\|faixa\|pagina arq` | prepara a imagem de capa |
| `revisar antes.html depois.html [--saida revisao.md]` | relatório do que a revisão de texto mudou; sai com 1 se houver item a conferir |
| `grafico extrair arq.docx` | lê os gráficos nativos do Word e grava a especificação em JSON |
| `grafico criar dados.json [--saida figura.html]` | gera o gráfico em SVG (barra, coluna, linha, rosca, pizza) no padrão da PGE |

## Opções do build

| Opção | Efeito |
|---|---|
| `--modo sobrio` (padrão) | tipografia, quadros, caixas e tabelas; serve a manual e apostila |
| `--modo completo` | acrescenta números-chave, linha do tempo e gráfico (blocos `so-completo`); para documento curto |
| `--saida arquivo.pdf` | nome do PDF final (padrão: `<html>-<modo>.pdf` ao lado do HTML) |
| `--conferir` | grava um PNG por página em `_conferencia/` |
| `--entrelinha 1.25` | entrelinha do corpo (padrão 1,22) |
| `--espaco-paragrafo 2.5` | espaço entre parágrafos em mm (padrão 3) |
| `--corpo 11.5` | corpo do texto em pt; escala toda a régua junto (padrão 12) |
| `--paleta agua` | cor de acento alternativa: `institucional` (padrão), `agua`, `marinho`, `bordo`, `bronze`, `laranja` |
| `--permitir-pendencias` | compila com `[PREENCHER]` no texto, só para teste |

O build também grava título e autor no PDF a partir de `<title>` e `vl-orgao`. Se o PDF estiver aberto em outro programa no Windows, ele grava `-NOVO.pdf` ao lado e avisa.

## Como o documento é montado

- **Capa e contracapa próprias.** Com `<meta name="vl-capa" content="propria">`, o build imprime a capa numa passada sem margem e sem cabeçalho, o corpo noutra, e a contracapa (`<section class="contracapa">`) numa terceira, e emenda as três. A capa e a contracapa não têm número; a paginação do rodapé conta a partir do expediente, que é a página 1.
- **Cabeçalho e rodapé** vêm do build, não do CSS (o Chromium ignora as margens do CSS paginado). Mexer neles é mexer em `scripts/build.py`.
- **Caminhos do design system.** O HTML aponta para `@ds/tokens.css`, `@ds/logo-pge.png` etc.; o build troca pelo caminho da skill numa cópia temporária que some ao fim. Imagens do documento ficam ao lado do HTML e entram por caminho relativo.
- **Número de página do sumário** depende do PDF; por isso `sumario` compila e relê. Rode de novo depois de qualquer mudança de texto.

## Quebra de página

Folga aceitável no pé: até uns 20 mm. Acima de 25 mm, quase sempre um bloco indivisível não coube. Resolva nesta ordem:

1. enxugue o bloco (menos texto, `pode-quebrar` em caixa ou tabela longa);
2. reordene, levando um bloco menor para o buraco;
3. só então force a quebra com `quebra-antes`.

A última página sempre sobra, e a página que termina antes de um título de seção também (o título não fica órfão no pé). Para ganhar uma página inteira, reduza `--entrelinha` (de 1,22 para 1,18, por exemplo): ela mexe no tamanho do documento muito mais do que o corpo da fonte. Não passe de 10 pt de corpo.

## Problemas conhecidos

- **Linha terminando em `art.`, `n.`, `§`, `Lei`**: falta `&nbsp;` depois do marcador. `checar --corrigir` insere; depois recompile e rode `sumario` de novo, porque o texto reflui.
- **Capa vazando para o corpo ou página sumindo**: o CSS declarou `display` duas vezes para `.capa-manual` ou `.contracapa`. Mantenha a regra única de `publicacao.css`.
- **Título do sumário "não encontrado no PDF"**: o texto do `s-tit` difere do título do corpo (acento, espaço, `&nbsp;`). Copie o título do corpo.
- **Fonte fora do padrão no PDF**: `doctor` aponta arquivo de fonte ausente em `assets/design-system/fonts/`.
- **`[PREENCHER]` bloqueia o build**: é proposital. Preencha ou apague o trecho.
- **Nota de rodapé com capa própria**: o build recusa. Use nota de rodapé só em documento curto.
- **Linha de tabela cortada no pé da página**: linha longa demais para a coluna; use `pode-quebrar` na tabela e encurte o texto.
- **PDF grande demais para e-mail**: as imagens da capa em 2480 px bastam; imagem maior não melhora o papel. Reduza a arte de origem com `imagem faixa`.
