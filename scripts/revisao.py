#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
revisao.py, relatório do que a revisão de texto mudou.

    dpge revisar corpo-original.html corpo.html [--saida revisao.md]

A revisão ortográfica e gramatical é feita sobre o HTML do corpo, só no texto,
sem tocar em tag, classe nem estrutura. Este comando compara a cópia guardada
antes (`corpo-original.html`) com a versão revisada e escreve um relatório,
bloco a bloco, com cada troca marcada: [-assim-] foi tirado, {+assim+} entrou.

Ele serve a duas coisas. Dá ao usuário uma lista que ele consegue ler e aprovar
antes de a diagramação seguir. E acusa o que uma revisão de texto não deveria
ter feito: mudar número, norma (art., Lei, §), citação entre aspas ou a
estrutura do documento (blocos juntados, tabelas ou figuras a mais ou a menos).
Esses itens saem marcados com ATENÇÃO e devem ser conferidos um a um.

Sai com código 1 se houver ATENÇÃO, para o fluxo não seguir sem conferência.
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

BLOCOS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "caption",
          "figcaption", "dt", "dd", "blockquote", "div"]
RE_TOKEN = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)
RE_NUMERO = re.compile(r"\d")
RE_NORMA = re.compile(r"(?i)\b(art|arts|lei|decreto|portaria|resolu[cç][aã]o|s[uú]mula|tema|inc|par|§)\b|§")
ASPAS = re.compile(r"[“\"][^”\"]{3,}[”\"]")


def blocos_de(caminho: Path) -> tuple:
    sopa = BeautifulSoup(caminho.read_text(encoding="utf-8"), "html.parser")
    textos = []
    for no in sopa.find_all(BLOCOS):
        # texto próprio do bloco: o que está nele e não num bloco aninhado.
        # `<li>texto<ol><li>filho</li></ol></li>` tem texto próprio e um filho
        # que se compara à parte; contar só a folha deixaria o pai de fora.
        proprio = [t for t in no.find_all(string=True) if t.find_parent(BLOCOS) is no]
        t = " ".join(" ".join(proprio).split())
        if t:
            textos.append(t)
    estrutura = {
        "tabelas": len(sopa.find_all("table")),
        "figuras": len(sopa.find_all(["img", "svg", "figure"])),
        "títulos": len(sopa.find_all(["h1", "h2", "h3", "h4"])),
    }
    return textos, estrutura


def diff_palavras(a: str, b: str) -> tuple:
    ta, tb = RE_TOKEN.findall(a), RE_TOKEN.findall(b)
    saida, trocas = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        velho, novo = "".join(ta[i1:i2]), "".join(tb[j1:j2])
        if op == "equal":
            saida.append(velho)
            continue
        if velho.strip():
            saida.append(f"[-{velho.strip()}-]")
        if novo.strip():
            saida.append(f"{{+{novo.strip()}+}}")
        if not velho.strip() and not novo.strip():
            saida.append(novo or velho)
        trocas.append((velho.strip(), novo.strip()))
    return re.sub(r"\s+", " ", "".join(saida)), trocas


def sensivel(trocas: list, antes: str, depois: str) -> list:
    """Motivos pelos quais a troca merece conferência do autor."""
    motivos = []
    for velho, novo in trocas:
        if RE_NUMERO.search(velho) or RE_NUMERO.search(novo):
            motivos.append("mexe em número")
            break
    for velho, novo in trocas:
        if RE_NORMA.search(velho) or RE_NORMA.search(novo):
            motivos.append("mexe em referência a norma")
            break
    if ASPAS.findall(antes) != ASPAS.findall(depois):
        motivos.append("mexe em trecho entre aspas (citação literal?)")
    return motivos


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("antes", type=Path, help="cópia do HTML antes da revisão")
    ap.add_argument("depois", type=Path, help="HTML revisado")
    ap.add_argument("--saida", type=Path, default=None, help="padrão: revisao.md ao lado do HTML revisado")
    args = ap.parse_args()
    for arq in (args.antes, args.depois):
        if not arq.is_file():
            print(f"erro: não encontrei {arq}", file=sys.stderr)
            return 1

    a, est_a = blocos_de(args.antes)
    b, est_b = blocos_de(args.depois)
    atencao_estrutura = [f"{k}: {est_a[k]} antes, {est_b[k]} depois"
                         for k in est_a if est_a[k] != est_b[k]]

    mudancas, itens_atencao = [], []
    alinhamento = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in alinhamento.get_opcodes():
        if op == "equal":
            continue
        if op == "replace" and (i2 - i1) == (j2 - j1):
            pares = list(zip(a[i1:i2], b[j1:j2]))
        elif op == "replace":
            # número de blocos diferente: pareia pelo mais parecido, o resto é estrutura
            pares = []
            sobra_a = list(a[i1:i2])
            for novo in b[j1:j2]:
                if not sobra_a:
                    pares.append(("", novo))
                    continue
                melhor = max(sobra_a, key=lambda x: difflib.SequenceMatcher(None, x, novo).ratio())
                sobra_a.remove(melhor)
                pares.append((melhor, novo))
            pares += [(x, "") for x in sobra_a]
        elif op == "delete":
            pares = [(x, "") for x in a[i1:i2]]
        else:
            pares = [("", x) for x in b[j1:j2]]
        for antes, depois in pares:
            if not antes or not depois:
                itens_atencao.append(("bloco inteiro " + ("removido" if not depois else "acrescentado"),
                                      antes or depois))
                continue
            marcado, trocas = diff_palavras(antes, depois)
            if not trocas:
                continue
            motivos = sensivel(trocas, antes, depois)
            mudancas.append((marcado, motivos))
            if motivos:
                itens_atencao.append(("; ".join(motivos), marcado))

    linhas = ["# Relatório de revisão", "",
              f"Comparado: `{args.antes.name}` com `{args.depois.name}`.",
              f"{len(mudancas)} bloco(s) de texto alterado(s) em {len(a)}.", ""]
    if atencao_estrutura:
        linhas += ["## ATENÇÃO: a estrutura mudou", ""] + [f"- {x}" for x in atencao_estrutura] + [""]
    if itens_atencao:
        linhas += ["## ATENÇÃO: conferir um a um", ""]
        linhas += [f"- ({m}) {t}" for m, t in itens_atencao] + [""]
    linhas += ["## Todas as alterações", "",
               "Convenção: `[-assim-]` foi tirado, `{+assim+}` entrou.", ""]
    linhas += [f"{i}. {m}" for i, (m, _) in enumerate(mudancas, 1)] or ["Nenhuma alteração."]
    destino = args.saida or args.depois.with_name("revisao.md")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print(f"relatório: {destino}")
    print(f"  {len(mudancas)} bloco(s) alterado(s); "
          f"{len(itens_atencao) + len(atencao_estrutura)} ponto(s) de ATENÇÃO")
    return 1 if (itens_atencao or atencao_estrutura) else 0


if __name__ == "__main__":
    raise SystemExit(main())
