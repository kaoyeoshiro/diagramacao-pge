#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
converter.py, transforma o texto de um .docx ou .md em HTML com as classes do
design system, pronto para colar no corpo do modelo.

    python scripts/dpge.py converter <arquivo.docx|.md> [--saida corpo.html]
                                     [--numerar] [--sumario sumario.html]

Gera dois fragmentos, não o documento inteiro:

    corpo.html     as seções e o texto, no padrão do modelo
    sumario.html   a lista do sumário, com `\u2014` no lugar dos números de página
                   (o `sumario` acerta os números depois de compilar)

Mapeamento:
    Título 1 / #     h2.secao        seção (caixa alta; começa página nova)
    Título 2 / ##    h3.subsecao     subseção
    Título 3 / ###   p.grupo         rótulo em negrito, fora do sumário
    tabela           table.dados     primeira linha vira cabeçalho
    lista            ul / ol         como está
    imagem           <img>           gravada em <saida>_imagens/

O que o conversor NÃO faz, e quem monta o documento precisa fazer: caixas de
síntese e de atenção, quadros de consulta, glossário, expediente e capa. Isso é
decisão de redação; o conversor entrega o texto limpo e as classes de estrutura.
Depois dele, rode `checar --corrigir` para os espaços não separáveis e as aspas.

Notas de rodapé do Word não são convertidas: o conversor avisa e as deixa em
lista no fim, para serem resolvidas à mão.
"""

import argparse
import html
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# "PARTE 3 – Título", "3. Título", "3.2.1. Título", "3.2 – Título"
RX_NUM = re.compile(
    r"^\s*(?:(?:PARTE|Parte|CAPÍTULO|Capítulo)\s+)?"
    r"(?P<num>\d+(?:\.\d+)*)\s*[.\u2013\u2014, \-]?\s*(?P<resto>\S.*)$"
)


def docx_para_html(caminho: Path, pasta_imagens: Path) -> str:
    import mammoth

    pasta_imagens.mkdir(parents=True, exist_ok=True)
    contador = {"n": 0}

    def salvar(imagem):
        contador["n"] += 1
        ext = (imagem.content_type or "image/png").split("/")[-1].replace("jpeg", "jpg")
        # O tipo vem do arquivo de origem: só letras e dígitos viram extensão,
        # para um .docx malformado não escolher onde a imagem é gravada.
        ext = re.sub(r"[^a-z0-9]", "", ext.lower())[:5] or "png"
        nome = f"img{contador['n']:03d}.{ext}"
        with imagem.open() as f:
            (pasta_imagens / nome).write_bytes(f.read())
        return {"src": f"{pasta_imagens.name}/{nome}"}

    with open(caminho, "rb") as f:
        r = mammoth.convert_to_html(
            f,
            convert_image=mammoth.images.img_element(salvar),
            style_map="\n".join([
                "p[style-name='Title'] => p.titulo-doc:fresh",
                "p[style-name='Título'] => p.titulo-doc:fresh",
            ]),
        )
    for m in r.messages:
        if m.type == "warning":
            print(f"  aviso do mammoth: {m.message}", file=sys.stderr)
    return r.value


def md_para_html(caminho: Path) -> str:
    import markdown

    return markdown.markdown(
        caminho.read_text(encoding="utf-8"),
        extensions=["tables", "sane_lists"],
    )


def limpar_texto(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def higienizar(sopa) -> None:
    """Tira do HTML convertido o que executa código ou busca arquivo fora da
    pasta do documento. O markdown deixa passar HTML cru, e o build abre o
    resultado num navegador; um texto de terceiros não pode rodar script nem
    puxar `file:///` para dentro do PDF."""
    for tag in sopa.find_all(["script", "style", "iframe", "object", "embed",
                              "link", "meta", "base", "form", "svg", "math"]):
        tag.decompose()
    for tag in sopa.find_all(True):
        for nome in list(tag.attrs):
            valor = tag.attrs[nome]
            if isinstance(valor, list):
                valor = " ".join(valor)
            if nome.lower().startswith("on") or nome.lower() == "style":
                del tag.attrs[nome]
            elif nome.lower() in ("src", "href", "srcset", "poster", "data"):
                v = re.sub(r"\s+", "", str(valor)).lower()
                externo = re.match(r"^[a-z][a-z0-9+.-]*:", v) or v.startswith(("/", "\\", "//")) or ".." in v.split("/")
                if nome.lower() == "href" and re.match(r"^(https?|mailto):", v):
                    continue
                if nome.lower() == "href" and v.startswith("#"):
                    continue
                if externo:
                    del tag.attrs[nome]


RX_NUMERICO = re.compile(r"^[\d.,%\s\u2212\-+R$/]+$")


def ajustar_tabela(t) -> None:
    """Classes de apresentação: `densa` a partir de seis colunas (para caber na
    largura útil) e `num` nas colunas só de número (alinhadas à direita)."""
    linhas = t.find_all("tr")
    if not linhas:
        return
    largura = sum(int(c.get("colspan", 1)) for c in linhas[0].find_all(["th", "td"]))
    if largura >= 6:
        t["class"] = t.get("class", []) + ["densa"]
    if any(c.has_attr("colspan") or c.has_attr("rowspan") for c in t.find_all(["th", "td"])):
        return
    corpo = [tr.find_all("td") for tr in linhas if tr.find("td")]
    for j in range(largura):
        col = [c[j].get_text(strip=True) for c in corpo if len(c) == largura]
        if col and all(v and RX_NUMERICO.match(v) for v in col):
            for tr in linhas:
                cels = tr.find_all(["th", "td"])
                if len(cels) == largura:
                    cels[j]["class"] = cels[j].get("class", []) + ["num"]


def estruturar(bruto: str, numerar: bool, sem_quebra: bool = False):
    """Aplica as classes do design system e devolve (corpo, itens do sumário)."""
    sopa = BeautifulSoup(bruto, "html.parser")
    higienizar(sopa)

    # parágrafos vazios e o título do documento (a capa cuida dele)
    for p in sopa.find_all("p"):
        if "titulo-doc" in (p.get("class") or []):
            p.decompose()
        elif not p.get_text(strip=True) and not p.find("img"):
            p.decompose()

    # negrito dentro de título é ruído: o título já é negrito
    for h in sopa.find_all(["h1", "h2", "h3", "h4"]):
        for b in h.find_all(["strong", "b", "em", "i"]):
            b.unwrap()

    itens = []
    n1 = n2 = 0
    for h in sopa.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        nivel = int(h.name[1])
        texto = limpar_texto(h.get_text())
        if nivel == 1:
            h.name, h["class"] = "h2", ["secao"] + ([] if sem_quebra else ["quebra-antes"])
        elif nivel == 2:
            h.name, h["class"] = "h3", ["subsecao"]
        else:
            h.name, h["class"] = "p", ["grupo"]
            h.string = texto
            continue

        m = RX_NUM.match(texto)
        if numerar:
            if nivel == 1:
                n1, n2 = n1 + 1, 0
                numero, titulo = str(n1), (m.group("resto") if m else texto)
            else:
                n2 += 1
                numero, titulo = f"{n1}.{n2}", (m.group("resto") if m else texto)
            h.clear()
            if nivel == 1:
                h.append(BeautifulSoup(
                    f'<span class="num">{numero}</span><span class="titulo">'
                    f'{html.escape(titulo)}</span>', "html.parser"))
            else:
                h.append(BeautifulSoup(
                    f'<span class="num">{numero}.</span> {html.escape(titulo)}',
                    "html.parser"))
        else:
            # o texto já traz a numeração ("PARTE 3 – ...", "3.1. ..."): mantém
            numero = m.group("num") if m else ""
            titulo = m.group("resto") if m else texto
            h.string = texto
        itens.append((nivel, numero, titulo))

    # tabelas: primeira linha é o cabeçalho
    for t in sopa.find_all("table"):
        t["class"] = ["dados"]
        linhas = t.find_all("tr")
        if linhas and not t.find("thead"):
            thead = sopa.new_tag("thead")
            tbody = sopa.new_tag("tbody")
            primeira = linhas[0]
            for c in primeira.find_all("td"):
                c.name = "th"
            thead.append(primeira.extract())
            for tr in linhas[1:]:
                tbody.append(tr.extract())
            for filho in list(t.children):
                if getattr(filho, "name", None) in ("tbody", "colgroup"):
                    filho.decompose()
            t.append(thead)
            t.append(tbody)
        ajustar_tabela(t)

    for img in sopa.find_all("img"):
        img.attrs.setdefault("alt", "")
        pai = img.parent
        # imagem sozinha no parágrafo vira figura: não parte entre páginas e
        # ganha legenda se o texto trouxer uma
        if pai.name == "p" and not pai.get_text(strip=True) and len(pai.find_all(True)) == 1:
            fig = sopa.new_tag("figure", attrs={"class": "figura"})
            pai.replace_with(fig)
            fig.append(img)

    # a numeração do próprio texto deixa "1." solto em listas aninhadas do Word
    corpo = sopa.decode(formatter="minimal").replace("\u00a0", "&nbsp;")
    # uma tag de bloco por linha, para o diff e a leitura
    corpo = re.sub(r"(</(?:p|h2|h3|ul|ol|table|li|thead|tbody|tr)>)", r"\1\n", corpo)
    return corpo.strip() + "\n", itens


def montar_sumario(itens) -> str:
    if not itens:
        return ""
    linhas = ['<div class="sumario">', "  <ol>"]
    for nivel, numero, titulo in itens:
        classe = "parte" if nivel == 1 else "sub"
        t = html.escape(titulo.upper() if nivel == 1 else titulo)
        linhas.append(
            f'    <li class="{classe}"><span class="s-num">{html.escape(numero)}</span>'
            f'<span class="s-tit"><span>{t}</span></span>'
            f'<span class="s-pag">\u2014</span></li>'
        )
    linhas += ["  </ol>", "</div>"]
    return "\n".join(linhas) + "\n"


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--saida", type=Path, default=None, help="padrão: <arquivo>-corpo.html")
    ap.add_argument("--sumario", type=Path, default=None,
                    help="padrão: <arquivo>-sumario.html")
    ap.add_argument("--sem-quebra", action="store_true", dest="sem_quebra",
                    help="não inicia cada seção (h2) em página nova; o padrão "
                         "inicia, que é o de manual e apostila")
    ap.add_argument("--numerar", action="store_true",
                    help="numera seções (1) e subseções (1.1) automaticamente; "
                         "use só se o texto de origem NÃO traz a numeração")
    args = ap.parse_args()

    if not args.arquivo.is_file():
        print(f"não encontrei {args.arquivo}", file=sys.stderr)
        return 1
    ext = args.arquivo.suffix.lower()
    saida = args.saida or args.arquivo.with_name(args.arquivo.stem + "-corpo.html")
    sumario = args.sumario or args.arquivo.with_name(args.arquivo.stem + "-sumario.html")

    if ext == ".docx":
        bruto = docx_para_html(args.arquivo, saida.with_name(saida.stem + "_imagens"))
    elif ext in (".md", ".markdown", ".txt"):
        bruto = md_para_html(args.arquivo)
    else:
        print("formatos aceitos: .docx, .md e .txt. PDF não: peça o arquivo de origem.",
              file=sys.stderr)
        return 1

    corpo, itens = estruturar(bruto, args.numerar, args.sem_quebra)
    saida.write_text(corpo, encoding="utf-8")
    sumario.write_text(montar_sumario(itens), encoding="utf-8")

    secoes = sum(1 for n, *_ in itens if n == 1)
    subs = sum(1 for n, *_ in itens if n == 2)
    print(f"corpo:    {saida}")
    print(f"sumário:  {sumario}")
    print(f"  {secoes} seções, {subs} subseções, "
          f"{corpo.count('<table')} tabelas, {corpo.count('<img')} imagens")
    if ext == ".docx":
        from grafico import contar_graficos
        graficos = contar_graficos(args.arquivo)
        if graficos:
            print(f"  AVISO: {graficos} gráfico(s) nativo(s) do Word não foram levados ao HTML "
                  f"(o Word guarda gráfico como objeto). Rode: grafico extrair {args.arquivo.name}",
                  file=sys.stderr)
    n_tab, n_img = corpo.count("<table"), corpo.count("<img")
    if n_tab or n_img:
        print(f"  Tabelas e imagens encontradas: pergunte ao usuário se quer refazê-las no "
              f"padrão da PGE (references/graficos-e-tabelas.md).")
    if not itens:
        print("  AVISO: nenhum título encontrado. O texto de origem usa estilos de "
              "título (Título 1, Título 2) ou # no Markdown?", file=sys.stderr)
    if re.search(r"footnote|endnote", bruto):
        print("  AVISO: o texto tem notas de rodapé do Word; resolva à mão.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
