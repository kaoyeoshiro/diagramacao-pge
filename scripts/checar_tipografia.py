#!/usr/bin/env python
"""Confere as regras de references/tipografia.md num documento.

    python scripts/dpge.py checar <documento.html>
    python scripts/dpge.py checar <documento.html> --corrigir

Sem `--corrigir` só relata. Com `--corrigir`, insere espaço não separável
depois dos marcadores de referência e troca `...` por `…` e aspas retas por
curvas, que são as correções mecânicas seguras. O resto é decisão de quem
escreve.

Se o PDF compilado existir ao lado do HTML (`<nome>-sobrio.pdf` ou
`<nome>-completo.pdf`, ou o que `--pdf` indicar), também mede a linha e procura
marcador órfão no fim de linha, que é a única forma de pegar a quebra que
escapou.
"""

from __future__ import annotations

import argparse
import re
import sys
from html import unescape
from pathlib import Path

# O console do Windows abre em cp1252 e estoura em “ ” … ×; sem isto o relatório
# morre no meio em vez de relatar.
for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

NBSP = " "

# Marcadores que não podem ficar separados do número que governam.
MARCADORES = (
    r"§§?|¶¶?|arts?\.|n\.|incs?\.|fls?\.|R\$|Exs?\.|Figs?\.|©"
    r"|Tema|Temas|Súmula|Súmulas|Lei|Leis|Decreto|Portaria|Resolução|Acórdão"
)
# Marcador + espaço em branco + número (arábico ou romano) ou "n.".
# O separador é `\s+` e não " " porque o fonte HTML quebra linha no meio da
# frase: `(art.` no fim de uma linha e `2º` no começo da seguinte vêm separados
# por quebra de linha, não por espaço. O HTML colapsa as duas coisas do mesmo
# jeito e a linha quebra ali igual. Era o que deixava 14 casos passarem pelo
# primeiro `--corrigir`.
# Espaço comum, tabulação ou quebra de linha, mas **não** o U+00A0: em Python
# `\s` casa com espaço não separável, e como o detector resolve as entidades
# antes de olhar o texto, `art.&nbsp;5º` voltava a ser acusado. Foram 82 falsos
# positivos numa peça já corrigida.
#
# O lookahead atravessa tags, porque `n. <span class="num">0000000</span>`
# tem o espaço dentro do nó de texto e quebra ali do mesmo jeito. E recusa
# `XX...` porque os modelos do manual usam `fls. XXX` como lacuna a preencher,
# e o detector lia isso como numeral romano.
# Entre o marcador e o número só pode haver tag inline. `<dt>Processo n.</dt>`
# seguido de `<dd>0000000...` está em outra célula da grade: nunca cai na mesma
# linha, e não há `&nbsp;` que sirva. Aceitar qualquer tag ali gerava um erro
# impossível de corrigir em toda peça que tem ficha de processo.
INLINE = r"</?(?:span|strong|b|em|i|a|sup|sub|abbr|code)\b[^>]*>"

RE_MARCADOR = re.compile(
    rf"(?<![\w.])({MARCADORES})[ \t\r\n]+"
    rf"(?=(?:{INLINE})*[ \t\r\n]*(?:\d|(?!X{{2}})[IVXLC]{{1,4}}[,.\s)]|n\.))"
)

# Comentário HTML entra junto: o modelo da skill explica os comandos dentro de
# comentários (`--saida`, `--ate-estabilizar`), e isso não é texto da publicação.
RE_STYLE = re.compile(r"<(style|script)\b.*?</\1>|<!--.*?-->", re.S | re.I)
RE_TAG = re.compile(r"<[^>]*>")


RE_BLOCO = re.compile(
    r"</?(?:p|div|dt|dd|li|ul|ol|table|thead|tbody|tr|td|th|caption|section"
    r"|article|h[1-6]|blockquote|figure|figcaption|br|hr)\b[^>]*>", re.I)


def texto_visivel(html: str) -> str:
    """Só o conteúdo textual: fora de tag, fora de <style> e <script>, com as
    entidades resolvidas.

    Duas sutilezas que custaram falso positivo. Resolver as entidades importa:
    `&nbsp;` vira U+00A0, que não casa com o espaço comum dos padrões, então
    marcador já colado deixa de ser acusado; e `&quot;` vira aspa reta e passa a
    ser acusado. E fronteira de bloco vira `\x00`, não espaço: sem isso o texto
    de duas células vizinhas cola numa frase que não existe, e o checador acusa
    quebra de linha entre coisas que nunca estiveram na mesma linha."""
    s = RE_STYLE.sub(" ", html)
    s = RE_BLOCO.sub("\x00", s)
    return unescape(RE_TAG.sub("", s))


def mapear_texto(html: str):
    """Fatias de `html` que são texto visível, como lista de (ini, fim)."""
    vazio = []
    for m in RE_STYLE.finditer(html):
        vazio.append(m.span())
    for m in RE_TAG.finditer(html):
        vazio.append(m.span())
    vazio.sort()
    fatias, pos = [], 0
    for ini, fim in vazio:
        if ini > pos:
            fatias.append((pos, ini))
        pos = max(pos, fim)
    if pos < len(html):
        fatias.append((pos, len(html)))
    return fatias


def sub_no_texto(html: str, padrao: re.Pattern, repl) -> tuple[str, int]:
    """Aplica substituição só nas fatias de texto visível.

    O padrão roda sobre o HTML inteiro e o casamento é descartado quando começa
    fora de um nó de texto. É diferente de rodar fatia por fatia: assim um
    lookahead pode atravessar tags, que é o que `n.&nbsp;<span>123</span>`
    exige. Casar fatia a fatia deixava esse caso sem correção enquanto o
    detector continuava acusando, e detector e corretor discordavam."""
    fatias = mapear_texto(html)

    def dentro(i: int) -> bool:
        return any(a <= i < b for a, b in fatias)

    partes, n, pos = [], 0, 0
    for m in padrao.finditer(html):
        if not dentro(m.start()):
            continue
        partes.append(html[pos:m.start()])
        partes.append(m.expand(repl) if isinstance(repl, str) else repl(m))
        pos = m.end()
        n += 1
    partes.append(html[pos:])
    return "".join(partes), n


# --------------------------------------------------------------------------
# Verificações no HTML
# --------------------------------------------------------------------------

def checar_html(caminho: Path):
    html = caminho.read_text(encoding="utf-8")
    txt = texto_visivel(html)
    achados: list[tuple[str, str, list[str]]] = []

    def add(nivel, titulo, exemplos):
        if exemplos:
            achados.append((nivel, titulo, exemplos))

    def amostras(padrao, alvo=None, n=6):
        alvo = txt if alvo is None else alvo
        vistos = []
        for m in re.finditer(padrao, alvo):
            ini = max(0, m.start() - 34)
            vistos.append("…" + " ".join(alvo[ini:m.end() + 14].split()) + "…")
            if len(vistos) >= n:
                break
        return vistos

    # lang
    m = re.search(r"<html[^>]*>", html, re.I)
    if not m or "pt-BR" not in m.group(0):
        add("ERRO", 'sem lang="pt-BR" no <html> (a hifenização usa o dicionário errado)',
            [m.group(0) if m else "<html> não encontrado"])

    # espaço não separável
    n_marc = len(RE_MARCADOR.findall(txt))
    if n_marc:
        add("ERRO",
            f"{n_marc} marcador(es) de referência com espaço comum em vez de &nbsp; "
            "(pode quebrar linha entre o marcador e o número)",
            amostras(RE_MARCADOR))

    # aspas retas
    add("ERRO", "aspas retas no texto (use “ ” ‘ ’)", amostras(r'["\']'))

    # reticência e travessão aproximados
    # `[...]` entre colchetes é a convenção brasileira de supressão em citação
    # e fica como está; só o `...` solto é defeito.
    add("ERRO", "três pontos no lugar da reticência …",
        amostras(r"(?<!\[)\.\.\.(?!\])"))
    add("ERRO", "hífen duplo no lugar do travessão —", amostras(r"(?<!-)--(?!-)"))

    # intervalo com hífen
    intervalos = amostras(r"\b(1[89]\d{2}|20\d{2})-(1[89]\d{2}|20\d{2})\b")
    intervalos += amostras(r"\b(fls?\.|pp?\.|arts?\.|incisos?)\s*\d{1,4}-\d{1,4}\b")
    add("AVISO", "intervalo com hífen (use meia-risca –)", intervalos[:6])

    # ordinal
    add("ERRO", "sinal de grau ° no lugar do ordinal º", amostras("°"))
    add("ERRO", "ordinal em <sup> (use º / ª)",
        amostras(r"<sup[^>]*>\s*[oa°º]", alvo=html))

    # sublinhado e versalete falso
    add("ERRO", "sublinhado (<u> ou text-decoration: underline)",
        amostras(r"<u\b|text-decoration:\s*underline", alvo=html))
    add("ERRO", "versalete falso (font-variant.*small-caps)",
        amostras(r"font-variant[^;:]*:\s*[^;]*small-caps", alvo=html))

    # n. x nº
    n_ponto = len(re.findall(r"\bn\.(?:\s|&nbsp;| )*(?=\d)", html))
    n_ord = len(re.findall(r"\bn[º°]", txt))
    if n_ponto and n_ord:
        add("AVISO",
            f"mistura de 'n.' ({n_ponto}) com 'nº' ({n_ord}); o padrão da casa é 'n.'",
            [f"{n_ponto}× n.  /  {n_ord}× nº"])

    # espaço duplo e espaço antes de pontuação, dentro de um nó de texto só
    duplos, antes = [], []
    for ini, fim in mapear_texto(html):
        no = html[ini:fim]
        for linha in no.splitlines():
            for m in re.finditer(r"\S {2,}\S", linha):
                duplos.append("…" + m.group(0) + "…")
            for m in re.finditer(r"\S +[.,;:!?)]", linha):
                antes.append("…" + m.group(0) + "…")
    add("AVISO", "espaço duplo no meio da frase", duplos[:6])
    add("ERRO", "espaço antes de pontuação", antes[:6])

    # espaço vertical feito de <br> ou parágrafo vazio
    add("AVISO", "<br> em sequência ou parágrafo vazio (espaço vertical é margem no CSS)",
        amostras(r"(<br\s*/?>\s*){2,}|<p>\s*(&nbsp;|\s)*</p>", alvo=html))

    return html, achados


# --------------------------------------------------------------------------
# Verificações no PDF compilado
# --------------------------------------------------------------------------

# No fim de linha só é defeito o marcador seguido de número na linha de baixo.
# "Lei" no fim da linha e "Complementar" na seguinte é quebra normal de palavra,
# não marcador órfão; sem checar o que vem depois, o relatório enche de falso
# positivo e ninguém olha mais para ele.
RE_ORFAO = re.compile(rf"(?:{MARCADORES})$")
# Só dígito, ou numeral romano que termine ali. `[IVXLC]` solto casaria com
# "Complementar" e "Vinculante", que começam com C e V.
# O `(?!X{2})` recusa `XXX`, que é a lacuna a preencher nos modelos do manual e
# não um numeral romano. Mesmo motivo do RE_MARCADOR.
RE_COMECA_NUM = re.compile(r"^\s*(?:\d|(?!X{2})[IVXLC]{1,4}(?:[\s,.)]|$))")

# Geometria da página, para medir a folga no pé. Espelha as margens do build.py.
PT = 72 / 25.4
TOPO_MM, BASE_MM = 31.0, 297.0 - 19.0
# Banda de abertura de página até esta altura é título ou quebra forçada, não
# bloco que não caiu: nesse caso a folga atrás é o `break-after: avoid`
# funcionando, e acusar isso como buraco é errar a régua.
ALT_TITULO_MM = 15.0
FOLGA_MAX_MM = 25.0


def bandas(pg):
    """Faixas verticais contíguas de conteúdo, texto e desenho juntos."""
    topo, base = TOPO_MM * PT, BASE_MM * PT
    itens = []
    for b in pg.get_text("blocks"):
        if b[1] > topo - 2 and b[3] < base + 2:
            itens.append((b[1], b[3], " ".join(b[4].split())[:46]))
    for d in pg.get_drawings():
        r = d["rect"]
        if r.y0 > topo - 2 and r.y1 < base + 2 and r.height > 2:
            itens.append((r.y0, r.y1, ""))
    itens.sort()
    faixas = []
    for y0, y1, t in itens:
        if faixas and y0 <= faixas[-1][1] + 3.5 * PT:
            faixas[-1][1] = max(faixas[-1][1], y1)
            faixas[-1][2] = faixas[-1][2] or t
        else:
            faixas.append([y0, y1, t])
    return faixas


def checar_pdf(pdf: Path, contracapa: bool = False):
    try:
        import pymupdf as fitz  # type: ignore
    except ImportError:
        return [("AVISO", f"{pdf.name}: pymupdf ausente, PDF não conferido", [])]

    doc = fitz.open(pdf)
    orfaos, cheias, buracos = [], [], []
    for i, pg in enumerate(doc, 1):
        for blk in pg.get_text("dict")["blocks"]:
            if blk["type"] != 0:
                continue
            linhas = ["".join(sp["text"] for sp in ln["spans"]) for ln in blk["lines"]]
            for k, ln in enumerate(blk["lines"]):
                t = linhas[k].rstrip()
                largura = (ln["bbox"][2] - ln["bbox"][0]) / PT
                if largura > 158:
                    cheias.append(len(t))
                seguinte = linhas[k + 1] if k + 1 < len(linhas) else ""
                if (largura > 100 and RE_ORFAO.search(t)
                        and RE_COMECA_NUM.match(seguinte)):
                    orfaos.append(f"pág. {i}: …{t[-38:]} / {seguinte[:14].strip()}…")

    # Folga no pé: só é buraco quando um bloco não caiu. Página que termina
    # antes de um título é o `break-after: avoid` fazendo o que deve.
    # A contracapa é página própria, curta de propósito: não é bloco que não caiu.
    for i in range(len(doc) - (2 if contracapa else 1)):
        atual, seg = bandas(doc[i]), bandas(doc[i + 1])
        if not atual or not seg:
            continue
        folga = (BASE_MM * PT - atual[-1][1]) / PT
        alt = (seg[0][1] - seg[0][0]) / PT
        if folga > FOLGA_MAX_MM and alt > ALT_TITULO_MM:
            # Bloco alto que não coube costuma ser ementa. `.precedente` não
            # começa partida (não deixa a barra colorida vazia no pé), e o
            # preço é este buraco quando a caixa é longa demais para o resto
            # da página. `.partivel` é a saída, e o aviso a nomeia porque
            # ninguém adivinha uma classe que não usou ainda.
            remedio = " — cabe `.partivel`" if alt > 45 else ""
            buracos.append(f"pág. {i+1}: {folga:.0f}mm — não caiu um bloco de "
                           f"{alt:.0f}mm{remedio}: {seg[0][2]!r}")
    doc.close()

    achados = []
    if orfaos:
        achados.append((
            "ERRO",
            f"{pdf.name}: {len(orfaos)} linha(s) terminando em marcador órfão",
            orfaos[:8],
        ))
    if buracos:
        achados.append((
            "AVISO",
            f"{pdf.name}: {len(buracos)} página(s) com buraco acima de "
            f"{FOLGA_MAX_MM:.0f}mm no pé. Enxugar o bloco, reordenar, marcar a "
            "citação longa com `.partivel`, e só então forçar a quebra",
            buracos[:8],
        ))
    if cheias:
        media = sum(cheias) / len(cheias)
        nivel = "AVISO" if media > 90 else "OK"
        achados.append((
            nivel,
            f"{pdf.name}: medida da linha, média de {media:.0f} caracteres "
            f"(faixa 45–90, máx. observado {max(cheias)})",
            [],
        ))
    return achados


# --------------------------------------------------------------------------
# Correção mecânica
# --------------------------------------------------------------------------

def corrigir(html: str) -> tuple[str, list[str]]:
    log = []
    html, n = sub_no_texto(html, RE_MARCADOR, lambda m: m.group(1) + "&nbsp;")
    if n:
        log.append(f"{n}× &nbsp; depois de marcador de referência")

    html, n = sub_no_texto(html, re.compile(r"(?<!\[)\.\.\.(?!\])"), "…")
    if n:
        log.append(f"{n}× ... → …")

    # aspas duplas: o par mais próximo, da esquerda para a direita
    # O par pode abrir num nó de texto e fechar depois de uma tag inline
    # ("<em>x</em>"): o estado atravessa tags e só zera na fronteira de bloco.
    partes, total, pos, aberto = [], 0, 0, False
    for ini, fim in mapear_texto(html):
        partes.append(html[pos:ini])
        if RE_BLOCO.search(html[pos:ini]):
            aberto = False
        saida = []
        for ch in html[ini:fim]:
            if ch == '"':
                saida.append("\u201d" if aberto else "\u201c")
                aberto = not aberto
                total += 1
            else:
                saida.append(ch)
        partes.append("".join(saida))
        pos = fim
    partes.append(html[pos:])
    html = "".join(partes)
    if total:
        log.append(f"{total}× aspa reta → curva")

    # apóstrofo
    html, n = sub_no_texto(html, re.compile(r"(?<=\w)'(?=\w)"), "’")
    if n:
        log.append(f"{n}× apóstrofo reto → curvo")

    # espaço antes de pontuação, dentro da mesma linha do fonte
    html, n = sub_no_texto(
        html, re.compile(r"(?<=\S)[ \t]+(?=[.,;:!?)])"), "")
    if n:
        log.append(f"{n}× espaço antes de pontuação removido")

    return html, log


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path, help="documento.html a conferir")
    ap.add_argument("--corrigir", action="store_true",
                    help="aplica as correções mecânicas seguras no arquivo")
    ap.add_argument("--pdf", type=Path, action="append", default=[],
                    help="PDF a conferir (pode repetir); padrão: os do próprio nome ao lado do HTML")
    ap.add_argument("--sem-pdf", action="store_true",
                    help="não confere os PDFs compilados ao lado do HTML")
    args = ap.parse_args()

    if not args.html.exists():
        print(f"não achei {args.html}")
        return 2

    html, achados = checar_html(args.html)

    if not args.sem_pdf:
        pdfs = args.pdf or [p for modo in ("sobrio", "completo")
                            if (p := args.html.parent / f"{args.html.stem}-{modo}.pdf").exists()]
        for pdf in pdfs:
            vivo = RE_STYLE.sub(" ", html)  # comentário não vale
            achados += checar_pdf(pdf, 'class="contracapa"' in vivo)

    erros = sum(1 for n, _, _ in achados if n == "ERRO")
    avisos = sum(1 for n, _, _ in achados if n == "AVISO")

    print(f"\n{args.html}")
    print("=" * 72)
    if not achados:
        print("nada a apontar.")
    for nivel, titulo, exemplos in achados:
        marca = {"ERRO": "[!]", "AVISO": "[~]", "OK": "[ok]"}[nivel]
        print(f"\n{marca} {titulo}")
        for e in exemplos:
            print(f"      {e}")
    print("\n" + "=" * 72)
    print(f"{erros} erro(s), {avisos} aviso(s).  Regras: references/tipografia.md")

    if args.corrigir:
        novo, log = corrigir(html)
        if novo != html:
            args.html.write_text(novo, encoding="utf-8")
            print(f"\ncorrigido {args.html}:")
            for l in log:
                print(f"      {l}")
            print("  recompilar e conferir; o reflow pode mexer na paginação.")
        else:
            print("\nnada a corrigir mecanicamente.")

    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
