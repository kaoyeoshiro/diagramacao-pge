#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grafico.py, gráficos no padrão visual da PGE-MS, sem biblioteca de gráfico.

    dpge grafico criar   dados.json [--saida figura.html]
    dpge grafico extrair documento.docx [--saida dados.json]

`criar` lê a especificação de um gráfico (ou uma lista deles) e escreve um
bloco HTML com o gráfico em SVG embutido, pronto para colar no documento. O SVG
herda a fonte do documento e usa só as cores do design system, então sai igual
aos demais componentes e escala com a largura da coluna.

`extrair` lê os gráficos nativos de um .docx (objetos de gráfico do Word, que o
conversor de texto não leva) e escreve a especificação de cada um, com os
valores que o Word guarda em cache, o tipo, o título e o parágrafo que vem antes
dele, para saber onde colar. Confira os números com o usuário antes de usar.

Especificação (JSON):

    {
      "tipo": "barra",              barra | coluna | linha | rosca | pizza
      "titulo": "Processos por área",
      "subtitulo": "Distribuição em 2025",       opcional
      "fonte": "Sistema X, janeiro de 2026",     opcional
      "rotulos": ["Tributário", "Saúde", "Pessoal"],
      "series": [{"nome": "2025", "valores": [120, 80, 45]}],
      "unidade": "",                opcional: "%", "R$", "dias"...
      "casas": 0,                   casas decimais exibidas
      "empilhado": false,           barra e coluna com mais de uma série
      "destaque": [0]               índices de rótulo em laranja (uma série só)
    }

Rosca e pizza usam a primeira série. Linha precisa de dois pontos ou mais.
"""

import argparse
import html
import json
import math
import re
import sys
import textwrap
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Cores do design system (tokens.css). Série 1 é o marinho; o laranja é
# destaque, então só entra como segunda série ou em `destaque`.
COR = ["#152B3F", "#F58634", "#51A8B1", "#366586", "#FAB370", "#8FA9BC"]
TEXTO_SOBRE = {"#152B3F": "#FFFFFF", "#366586": "#FFFFFF"}  # o resto leva marinho
MARINHO = "#152B3F"
CINZA_TEXTO = "#6E7C88"
CINZA_LINHA = "#DCDDDF"
LARANJA = "#F58634"

W = 640           # largura do desenho; 1 unidade = 0,25 mm na coluna de 160 mm
F_ROT = 12.5      # ~9 pt
F_VAL = 12.5
F_EIXO = 11.5
CHAR = 0.5        # largura média de um caractere, em múltiplos do corpo

MARCAS = ["circulo", "quadrado", "losango", "triangulo", "circulo", "quadrado"]

TIPOS = ("barra", "coluna", "linha", "rosca", "pizza")


class Erro(ValueError):
    pass


def esc(t) -> str:
    return html.escape(str(t), quote=True)


def fmt(v: float, casas: int, unidade: str = "") -> str:
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if unidade in ("%", "p.p."):
        return f"{s}{unidade}" if unidade == "%" else f"{s} {unidade}"
    if unidade:
        return f"{unidade} {s}" if unidade in ("R$", "US$", "€") else f"{s} {unidade}"
    return s


def quebrar(t: str, largura: int, linhas: int = 3) -> list:
    partes = textwrap.wrap(str(t), width=max(largura, 6), break_long_words=True) or [""]
    if len(partes) > linhas:
        partes = partes[:linhas]
        partes[-1] = partes[-1][: max(largura - 1, 1)] + "…"
    return partes


def texto(x, y, t, tam=F_ROT, peso=400, cor=MARINHO, ancora="start") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" font-weight="{peso}" '
            f'fill="{cor}" text-anchor="{ancora}">{esc(t)}</text>')


def escala_bonita(maximo: float, minimo: float = 0.0, alvo: int = 5):
    """Limites e passo 'redondos' para o eixo (1, 2, 2,5 ou 5 vezes 10^k)."""
    if maximo <= minimo:
        maximo = minimo + 1
    bruto = (maximo - minimo) / alvo
    base = 10 ** math.floor(math.log10(bruto))
    passo = min((m * base for m in (1, 2, 2.5, 5, 10) if m * base >= bruto),
                default=10 * base)
    lo = math.floor(minimo / passo) * passo
    hi = math.ceil(maximo / passo) * passo
    return lo, hi, passo


def legenda(series, y, x0=0, largura=W, quadrada=False) -> tuple:
    """Itens lado a lado, quebrando linha. Devolve (svg, altura)."""
    x, linha, partes = x0, 0, []
    for i, s in enumerate(series):
        nome = str(s["nome"])
        w = 18 + len(nome) * F_ROT * CHAR + 18
        if x + w > x0 + largura and x > x0:
            x, linha = x0, linha + 1
        cy = y + linha * 20
        partes.append(marca(x + 6, cy - 4, COR[i % len(COR)],
                            "quadrado" if quadrada else MARCAS[i % len(MARCAS)], 6))
        partes.append(texto(x + 17, cy, nome))
        x += w
    return "".join(partes), (linha + 1) * 20


def marca(cx, cy, cor, forma, r) -> str:
    if forma == "quadrado":
        return f'<rect x="{cx-r:.1f}" y="{cy-r:.1f}" width="{2*r}" height="{2*r}" fill="{cor}"/>'
    if forma == "losango":
        return (f'<polygon points="{cx:.1f},{cy-r*1.2:.1f} {cx+r*1.2:.1f},{cy:.1f} '
                f'{cx:.1f},{cy+r*1.2:.1f} {cx-r*1.2:.1f},{cy:.1f}" fill="{cor}"/>')
    if forma == "triangulo":
        return (f'<polygon points="{cx:.1f},{cy-r*1.2:.1f} {cx+r*1.1:.1f},{cy+r:.1f} '
                f'{cx-r*1.1:.1f},{cy+r:.1f}" fill="{cor}"/>')
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{cor}"/>'


# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------

def desenhar_barra(e: dict) -> tuple:
    rot, series = e["rotulos"], e["series"]
    casas, un = e["casas"], e["unidade"]
    n, ns = len(rot), len(series)
    emp = e["empilhado"] and ns > 1
    cat = [quebrar(r, 30, 3) for r in rot]
    esq = min(max(len(l) for ls in cat for l in ls) * F_ROT * CHAR + 14, 250)
    totais = [sum(s["valores"][i] for s in series) for i in range(n)]
    candidatos = totais if emp else [v for s in series for v in s["valores"]]
    dir_ = max(len(fmt(v, casas, un)) for v in candidatos) * F_VAL * 0.58 + 14
    x0, x1 = esq, W - dir_
    maximo = max(totais) if emp else max(v for s in series for v in s["valores"])
    maximo = maximo if maximo > 0 else 1
    bh = 18 if (ns == 1 or emp) else 13
    folga = 16
    parte, y = [], 0.0
    if ns > 1:
        svg, alt = legenda(series, 12, quadrada=True)
        parte.append(svg)
        y = alt + 10
    inicio = y
    for i in range(n):
        linhas = cat[i]
        alt_banda = bh if (ns == 1 or emp) else ns * bh + (ns - 1) * 2
        meio = y + alt_banda / 2
        topo_txt = meio - (len(linhas) - 1) * 7.5 + 4.2
        for k, l in enumerate(linhas):
            parte.append(texto(esq - 10, topo_txt + k * 15, l, ancora="end", peso=600))
        if emp:
            x = x0
            for j, s in enumerate(series):
                v = s["valores"][i]
                w = v / maximo * (x1 - x0)
                cor = COR[j % len(COR)]
                parte.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bh}" fill="{cor}"/>')
                if w > 34:
                    parte.append(texto(x + w / 2, y + bh / 2 + 4, fmt(v, casas), 11,
                                       600, TEXTO_SOBRE.get(cor, MARINHO), "middle"))
                x += w
            parte.append(texto(x + 6, y + bh / 2 + 4.2, fmt(totais[i], casas, un), F_VAL, 700))
        else:
            destaque = i in e["destaque"] and ns == 1
            for j, s in enumerate(series):
                v = s["valores"][i]
                w = max(v / maximo * (x1 - x0), 1.5)
                yy = y + j * (bh + 2)
                cor = LARANJA if destaque else COR[j % len(COR)]
                parte.append(f'<rect x="{x0:.1f}" y="{yy:.1f}" width="{w:.1f}" height="{bh}" fill="{cor}"/>')
                parte.append(texto(x0 + w + 6, yy + bh / 2 + 4.2, fmt(v, casas, un),
                                   F_VAL if ns == 1 else 11, 700))
        y += alt_banda + folga
    altura = y - folga + 6
    parte.append(f'<line x1="{x0}" y1="{inicio - 4:.1f}" x2="{x0}" y2="{altura - 2:.1f}" '
                 f'stroke="{MARINHO}" stroke-width="1"/>')
    return "".join(parte), altura


def desenhar_coluna(e: dict) -> tuple:
    rot, series = e["rotulos"], e["series"]
    casas, un = e["casas"], e["unidade"]
    n, ns = len(rot), len(series)
    emp = e["empilhado"] and ns > 1
    esq, dir_ = 8, 8
    ph = 210.0
    topo = 22.0
    y0 = topo
    parte = []
    if ns > 1:
        svg, alt = legenda(series, 12, quadrada=True)
        parte.append(svg)
        y0 = alt + 24
    totais = [sum(s["valores"][i] for s in series) for i in range(n)]
    maximo = max(totais) if emp else max(v for s in series for v in s["valores"])
    maximo = maximo if maximo > 0 else 1
    base = y0 + ph
    largura = W - esq - dir_
    banda = largura / n
    gap = min(banda * 0.28, 30)
    larg = banda - gap
    if not emp and ns > 1:
        bw = larg / ns
    else:
        bw = larg
    # linha de base
    parte.append(f'<line x1="{esq}" y1="{base:.1f}" x2="{W - dir_}" y2="{base:.1f}" '
                 f'stroke="{MARINHO}" stroke-width="1"/>')
    carac = int(banda / (F_ROT * CHAR)) - 1
    max_linhas = 1
    for i in range(n):
        cx0 = esq + i * banda + gap / 2
        if emp:
            acumulado = 0.0
            for j, s in enumerate(series):
                v = s["valores"][i]
                h = v / maximo * ph
                cor = COR[j % len(COR)]
                parte.append(f'<rect x="{cx0:.1f}" y="{base - (acumulado + v) / maximo * ph:.1f}" '
                             f'width="{larg:.1f}" height="{h:.1f}" fill="{cor}"/>')
                if h > 18:
                    parte.append(texto(cx0 + larg / 2, base - acumulado / maximo * ph - h / 2 + 4,
                                       fmt(v, casas), 11, 600, TEXTO_SOBRE.get(cor, MARINHO), "middle"))
                acumulado += v
            parte.append(texto(cx0 + larg / 2, base - acumulado / maximo * ph - 6,
                               fmt(totais[i], casas, un), F_VAL, 700, ancora="middle"))
        else:
            destaque = i in e["destaque"] and ns == 1
            for j, s in enumerate(series):
                v = s["valores"][i]
                h = max(v / maximo * ph, 1.5)
                cor = LARANJA if destaque else COR[j % len(COR)]
                x = cx0 + j * bw
                parte.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw - (1.5 if ns > 1 else 0):.1f}" '
                             f'height="{h:.1f}" fill="{cor}"/>')
                parte.append(texto(x + (bw - (1.5 if ns > 1 else 0)) / 2, base - h - 6,
                                   fmt(v, casas, un if ns == 1 else ""), F_VAL if ns == 1 else 10.5,
                                   700, ancora="middle"))
        ls = quebrar(rot[i], carac, 3)
        max_linhas = max(max_linhas, len(ls))
        for k, l in enumerate(ls):
            parte.append(texto(cx0 + larg / 2, base + 17 + k * 14.5, l, ancora="middle", peso=600))
    return "".join(parte), base + 17 + (max_linhas - 1) * 14.5 + 8


def desenhar_linha(e: dict) -> tuple:
    rot, series = e["rotulos"], e["series"]
    casas, un = e["casas"], e["unidade"]
    n, ns = len(rot), len(series)
    todos = [v for s in series for v in s["valores"]]
    lo, hi, passo = escala_bonita(max(todos), min(0.0, min(todos)))
    # casas do eixo: as pedidas e as que o passo exige (passo 0,5 pede uma)
    casas_eixo = max(casas, math.ceil(-math.log10(passo) - 1e-9) if passo < 1 else 0)
    esq = max(len(fmt(hi, casas_eixo, un)), len(fmt(lo, casas_eixo, un))) * F_EIXO * CHAR + 14
    dir_ = 20
    ph = 200.0
    y0 = 24.0
    parte = []
    if ns > 1:
        svg, alt = legenda(series, 12)
        parte.append(svg)
        y0 = alt + 26
    base = y0 + ph
    largura = W - esq - dir_

    def X(i):
        return esq + (largura * i / (n - 1) if n > 1 else largura / 2)

    def Y(v):
        return base - (v - lo) / (hi - lo) * ph

    v = lo
    while v <= hi + passo / 1000:
        yy = Y(v)
        parte.append(f'<line x1="{esq:.1f}" y1="{yy:.1f}" x2="{W - dir_}" y2="{yy:.1f}" '
                     f'stroke="{CINZA_LINHA if v != 0 else MARINHO}" stroke-width="1"/>')
        parte.append(texto(esq - 8, yy + 4, fmt(v, casas_eixo, un if un in ("%",) else ""),
                           F_EIXO, 400, CINZA_TEXTO, "end"))
        v += passo
    carac = int((largura / max(n - 1, 1)) / (F_ROT * CHAR)) - 1
    max_linhas = 1
    for i in range(n):
        ls = quebrar(rot[i], max(carac, 8), 2)
        max_linhas = max(max_linhas, len(ls))
        for k, l in enumerate(ls):
            ancora = "middle" if 0 < i < n - 1 else ("start" if i == 0 and n > 1 else "end")
            xt = X(i) if ancora == "middle" else (esq - 4 if ancora == "start" else W - dir_ + 8)
            parte.append(texto(xt, base + 17 + k * 14.5, l, ancora=ancora, peso=600))
    rotular = ns <= 2 and n <= 9
    for j, s in enumerate(series):
        cor = COR[j % len(COR)]
        pts = " ".join(f"{X(i):.1f},{Y(val):.1f}" for i, val in enumerate(s["valores"]))
        parte.append(f'<polyline points="{pts}" fill="none" stroke="{cor}" stroke-width="2.6" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        for i, val in enumerate(s["valores"]):
            parte.append(marca(X(i), Y(val), cor, MARCAS[j % len(MARCAS)], 4.4))
            if rotular:
                acima = (j == 0) or ns == 1
                parte.append(texto(X(i), Y(val) + (-10 if acima else 19),
                                   fmt(val, casas, un if ns == 1 else ""), 11, 700, cor if cor != "#F58634" else "#C16C2F",
                                   "middle"))
    return "".join(parte), base + 17 + (max_linhas - 1) * 14.5 + 8


def arco(cx, cy, r_ext, r_int, a0, a1) -> str:
    """Setor de rosca entre os ângulos a0 e a1 (radianos, 0 = topo, sentido horário)."""
    def p(r, a):
        return cx + r * math.sin(a), cy - r * math.cos(a)

    grande = 1 if a1 - a0 > math.pi else 0
    xe0, ye0 = p(r_ext, a0)
    xe1, ye1 = p(r_ext, a1)
    if r_int > 0:
        xi1, yi1 = p(r_int, a1)
        xi0, yi0 = p(r_int, a0)
        return (f"M{xe0:.2f},{ye0:.2f} A{r_ext},{r_ext} 0 {grande} 1 {xe1:.2f},{ye1:.2f} "
                f"L{xi1:.2f},{yi1:.2f} A{r_int},{r_int} 0 {grande} 0 {xi0:.2f},{yi0:.2f} Z")
    return (f"M{cx:.2f},{cy:.2f} L{xe0:.2f},{ye0:.2f} "
            f"A{r_ext},{r_ext} 0 {grande} 1 {xe1:.2f},{ye1:.2f} Z")


def desenhar_rosca(e: dict) -> tuple:
    rot, valores = e["rotulos"], e["series"][0]["valores"]
    casas, un = e["casas"], e["unidade"]
    total = sum(valores)
    r_ext = 92.0
    r_int = 0.0 if e["tipo"] == "pizza" else 56.0
    cx, cy = 20 + r_ext, 12 + r_ext
    parte = []
    ang = 0.0
    for i, v in enumerate(valores):
        a1 = ang + (v / total) * 2 * math.pi
        cor = COR[i % len(COR)]
        if len(valores) == 1 or v >= total - 1e-9:
            parte.append(f'<circle cx="{cx}" cy="{cy}" r="{r_ext}" fill="{cor}"/>')
            if r_int:
                parte.append(f'<circle cx="{cx}" cy="{cy}" r="{r_int}" fill="#FFFFFF"/>')
        elif v > 0:
            parte.append(f'<path d="{arco(cx, cy, r_ext, r_int, ang, a1)}" fill="{cor}" '
                         f'stroke="#FFFFFF" stroke-width="1.5"/>')
        ang = a1
    if r_int and e.get("total"):
        parte.append(texto(cx, cy - 2, fmt(total, casas), 20, 700, ancora="middle"))
        parte.append(texto(cx, cy + 15, str(e["total"]), 11, 400, CINZA_TEXTO, "middle"))
    # legenda à direita: cor, rótulo, valor e percentual
    lx = 2 * r_ext + 20 + 36
    ly = max(cy - len(rot) * 11, 18)
    carac = int((W - lx - 120) / (F_ROT * CHAR))
    y = ly
    for i, r in enumerate(rot):
        ls = quebrar(r, carac, 2)
        cor = COR[i % len(COR)]
        parte.append(f'<rect x="{lx}" y="{y - 10:.1f}" width="12" height="12" fill="{cor}"/>')
        for k, l in enumerate(ls):
            parte.append(texto(lx + 20, y + k * 14.5, l, peso=600))
        pct = fmt(valores[i] / total * 100, 1, "%")
        parte.append(texto(W - 4, y, f"{fmt(valores[i], casas, un)} ({pct})", F_VAL, 700, ancora="end"))
        y += max(len(ls) * 14.5, 14.5) + 9
    return "".join(parte), max(2 * r_ext + 24, y)


DESENHO = {"barra": desenhar_barra, "coluna": desenhar_coluna, "linha": desenhar_linha,
           "rosca": desenhar_rosca, "pizza": desenhar_rosca}


# --------------------------------------------------------------------------
# Validação e montagem
# --------------------------------------------------------------------------

def validar(spec: dict, n: int = 1) -> dict:
    if not isinstance(spec, dict):
        raise Erro(f"gráfico {n}: a especificação precisa ser um objeto JSON com tipo, rotulos e series")
    ref = f"gráfico {n}" + (f" ({spec.get('titulo')})" if spec.get("titulo") else "")
    tipo = str(spec.get("tipo", "")).lower()
    if tipo not in TIPOS:
        raise Erro(f"{ref}: tipo '{tipo}' desconhecido; use {', '.join(TIPOS)}")
    rot = spec.get("rotulos") or []
    series = spec.get("series") or []
    if not rot or not series:
        raise Erro(f"{ref}: faltam rotulos ou series")
    limpas = []
    for s in series:
        if not isinstance(s, dict):
            raise Erro(f"{ref}: cada série precisa ser um objeto com nome e valores")
        vals = s.get("valores") or []
        if len(vals) != len(rot):
            raise Erro(f"{ref}: a série '{s.get('nome')}' tem {len(vals)} valores para {len(rot)} rótulos")
        if any(v is None for v in vals):
            raise Erro(f"{ref}: valor ausente (null) na série '{s.get('nome')}'; preencha com o "
                       "dado confirmado pelo usuário")
        try:
            vals = [float(v) for v in vals]
        except (TypeError, ValueError):
            raise Erro(f"{ref}: valor que não é número na série '{s.get('nome')}'")
        if any(not math.isfinite(v) for v in vals):
            raise Erro(f"{ref}: valor infinito ou NaN na série '{s.get('nome')}'")
        limpas.append({"nome": s.get("nome", ""), "valores": vals})
    if tipo in ("rosca", "pizza"):
        limpas = limpas[:1]
        if any(v < 0 for v in limpas[0]["valores"]) or sum(limpas[0]["valores"]) <= 0:
            raise Erro(f"{ref}: rosca e pizza precisam de valores positivos")
        if len(rot) > len(COR):
            raise Erro(f"{ref}: rosca e pizza aceitam até {len(COR)} fatias (as cores acabam); "
                       "agrupe o restante em 'Outros' ou use barra")
    if tipo == "linha" and len(rot) < 2:
        raise Erro(f"{ref}: linha precisa de dois pontos ou mais")
    if tipo in ("barra", "coluna") and any(v < 0 for s in limpas for v in s["valores"]):
        raise Erro(f"{ref}: barra e coluna não aceitam valor negativo; use linha")
    if len(limpas) > len(COR):
        raise Erro(f"{ref}: no máximo {len(COR)} séries; separe em dois gráficos")
    try:
        casas = int(spec.get("casas", 0))
        bruto = spec.get("destaque", [])
        destaque = [int(i) for i in (bruto if isinstance(bruto, list) else [bruto])]
    except (TypeError, ValueError):
        raise Erro(f"{ref}: 'casas' e 'destaque' precisam ser números inteiros")
    if not 0 <= casas <= 6:
        raise Erro(f"{ref}: 'casas' vai de 0 a 6")
    return {
        "tipo": tipo, "titulo": spec.get("titulo", ""), "subtitulo": spec.get("subtitulo", ""),
        "fonte": spec.get("fonte", ""), "rotulos": [str(r) for r in rot], "series": limpas,
        "unidade": str(spec.get("unidade", "")), "casas": casas,
        "empilhado": bool(spec.get("empilhado", False)),
        "destaque": destaque, "total": spec.get("total", ""),
    }


def montar(spec: dict, n: int = 1) -> str:
    e = validar(spec, n)
    corpo, altura = DESENHO[e["tipo"]](e)
    descricao = f"{e['titulo'] or 'Gráfico'}. " + "; ".join(
        f"{r}: " + ", ".join(fmt(s["valores"][i], e["casas"], e["unidade"]) for s in e["series"])
        for i, r in enumerate(e["rotulos"]))
    partes = ['<div class="grafico">']
    if e["titulo"]:
        partes.append(f'  <div class="grafico-titulo">{esc(e["titulo"])}</div>')
    if e["subtitulo"]:
        partes.append(f'  <div class="grafico-sub">{esc(e["subtitulo"])}</div>')
    partes.append(f'  <svg viewBox="0 0 {W} {altura:.0f}" role="img" aria-label="{esc(descricao)}" '
                  f'xmlns="http://www.w3.org/2000/svg" class="grafico-svg">{corpo}</svg>')
    if e["fonte"]:
        partes.append(f'  <div class="grafico-fonte">Fonte: {esc(e["fonte"])}</div>')
    partes.append("</div>")
    return "\n".join(partes) + "\n"


# --------------------------------------------------------------------------
# Extração dos gráficos nativos do Word
# --------------------------------------------------------------------------

NS = {
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
MAPA_TIPO = {"barChart": "barra", "bar3DChart": "barra", "lineChart": "linha",
             "line3DChart": "linha", "areaChart": "linha", "area3DChart": "linha",
             "pieChart": "pizza", "pie3DChart": "pizza", "doughnutChart": "rosca",
             "ofPieChart": "pizza"}


def _xml(dados: bytes):
    """Parser do stdlib, com a porta de DTD fechada: XML de Office não tem
    DOCTYPE, e arquivo malformado com entidades recursivas travaria a leitura."""
    if b"<!DOCTYPE" in dados or b"<!ENTITY" in dados:
        raise Erro("o arquivo traz declaração de entidade XML, o que um documento do Office "
                   "não tem; recuso abrir")
    return ET.fromstring(dados)


def _pontos(no) -> list:
    """Valores de um c:strCache / c:numCache, na ordem do índice."""
    if no is None:
        return []
    cache = no.find(".//c:strCache", NS)
    if cache is None:
        cache = no.find(".//c:numCache", NS)
    if cache is None:
        return []
    cont = cache.find("c:ptCount", NS)
    try:
        n = int(cont.get("val")) if cont is not None else 0
    except (TypeError, ValueError):
        n = 0
    if not 0 <= n <= 1000:
        raise Erro("o gráfico declara mais de 1000 pontos; recuso abrir")
    out = [""] * n
    for pt in cache.findall("c:pt", NS):
        try:
            i = int(pt.get("idx"))
        except (TypeError, ValueError):
            continue
        v = pt.find("c:v", NS)
        if 0 <= i < len(out):
            out[i] = v.text if v is not None and v.text is not None else ""
    return out


def _numero(v: str):
    """Número do cache do Word, ou None se a célula está vazia ou não é número
    (#N/A, texto): zero inventado seria dado novo no gráfico."""
    try:
        x = float((v or "").strip())
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _chart_para_spec(xml: bytes, contexto: str, n: int) -> dict:
    raiz = _xml(xml)
    plot = raiz.find(".//c:plotArea", NS)
    tipo_xml, grafico = None, None
    for filho in (plot if plot is not None else []):
        nome = filho.tag.split("}")[-1]
        if nome in MAPA_TIPO or nome in ("scatterChart", "bubbleChart", "radarChart",
                                         "stockChart", "surfaceChart", "surface3DChart"):
            tipo_xml, grafico = nome, filho
            break
    titulo = "".join(t.text or "" for t in raiz.findall(".//c:chart/c:title//a:t", NS)).strip()
    spec = {"_origem": f"gráfico {n} do Word", "_contexto": contexto, "titulo": titulo,
            "subtitulo": "", "fonte": "", "unidade": "", "casas": 0}
    if grafico is None or tipo_xml not in MAPA_TIPO:
        spec["tipo"] = ""
        spec["_aviso"] = (f"tipo '{tipo_xml or 'desconhecido'}' não é suportado; "
                          "refaça à mão com os dados que o usuário confirmar")
        return spec
    spec["tipo"] = MAPA_TIPO[tipo_xml]
    if tipo_xml in ("barChart", "bar3DChart"):
        direcao = grafico.find("c:barDir", NS)
        spec["tipo"] = "coluna" if direcao is not None and direcao.get("val") == "col" else "barra"
        agrup = grafico.find("c:grouping", NS)
        spec["empilhado"] = agrup is not None and agrup.get("val") in ("stacked", "percentStacked")
    series, rotulos = [], []
    for ser in grafico.findall("c:ser", NS):
        nome = " ".join(_pontos(ser.find("c:tx", NS))).strip() or f"Série {len(series) + 1}"
        cats = _pontos(ser.find("c:cat", NS))
        vals = _pontos(ser.find("c:val", NS))
        if not rotulos:
            rotulos = cats or [str(i + 1) for i in range(len(vals))]
        series.append({"nome": nome, "valores": [_numero(v) for v in vals]})
    spec["rotulos"], spec["series"] = rotulos, series
    ausentes = sum(v is None for s in series for v in s["valores"])
    if ausentes:
        spec["_aviso"] = (f"{ausentes} valor(es) ausente(s) ou ilegível(is) ficaram como null; "
                          "confirme com o usuário e preencha antes de rodar `grafico criar`")
    achados = [v for s in series for v in s["valores"] if v is not None]
    spec["casas"] = 0 if all(abs(v - round(v)) < 1e-9 for v in achados) else 1
    return spec


def extrair(docx: Path) -> list:
    with zipfile.ZipFile(docx) as z:
        nomes = z.namelist()
        rels = {r.get("Id"): r.get("Target")
                for r in _xml(z.read("word/_rels/document.xml.rels")).iter(RELS)}
        doc = _xml(z.read("word/document.xml"))
        specs, contexto, n = [], "", 0
        for par in doc.iter("{%s}p" % NS["w"]):
            texto_p = "".join(t.text or "" for t in par.iter("{%s}t" % NS["w"])).strip()
            for ch in par.iter("{%s}chart" % NS["c"]):
                alvo = rels.get(ch.get("{%s}id" % NS["r"]), "")
                caminho = "word/" + alvo.lstrip("/").replace("word/", "", 1)
                if caminho not in nomes:
                    continue
                n += 1
                specs.append(_chart_para_spec(z.read(caminho), contexto, n))
            if texto_p:
                contexto = texto_p[:140]
    return specs


def contar_graficos(docx: Path) -> int:
    """Quantos gráficos nativos o Word tem; 0 se o arquivo não abre."""
    try:
        with zipfile.ZipFile(docx) as z:
            return sum(1 for nome in z.namelist() if re.fullmatch(r"word/charts/chart\d+\.xml", nome))
    except (zipfile.BadZipFile, OSError):
        return 0


# --------------------------------------------------------------------------

def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar", help="gera o HTML do gráfico a partir da especificação")
    c.add_argument("dados", type=Path)
    c.add_argument("--saida", type=Path)
    x = sub.add_parser("extrair", help="lê os gráficos nativos de um .docx")
    x.add_argument("docx", type=Path)
    x.add_argument("--saida", type=Path)
    args = ap.parse_args()

    if not args.__dict__.get("dados", args.__dict__.get("docx")).exists():
        print("erro: arquivo não encontrado", file=sys.stderr)
        return 1

    if args.cmd == "criar":
        try:
            bruto = json.loads(args.dados.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"erro: JSON inválido em {args.dados}: {exc}", file=sys.stderr)
            return 1
        lista = bruto if isinstance(bruto, list) else [bruto]
        try:
            saida = "\n".join(montar(s, i + 1) for i, s in enumerate(lista))
        except Erro as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        destino = args.saida or args.dados.with_suffix(".html")
        destino.write_text(saida, encoding="utf-8")
        print(f"{len(lista)} gráfico(s) em {destino}")
        return 0

    try:
        specs = extrair(args.docx)
    except (Erro, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        print(f"erro: não consegui ler {args.docx.name} como .docx ({exc})", file=sys.stderr)
        return 1
    destino = args.saida or args.docx.with_name(args.docx.stem + "-graficos.json")
    destino.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(specs)} gráfico(s) nativo(s) do Word em {destino}")
    for s in specs:
        aviso = f"  [{s['_aviso']}]" if s.get("_aviso") else ""
        print(f"  - {s['_origem']}: {s['titulo'] or '(sem título)'}; vem depois de: "
              f"\"{s['_contexto'][:60]}\"{aviso}")
    if specs:
        print("Confira os valores com o usuário e rode `grafico criar` no arquivo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
