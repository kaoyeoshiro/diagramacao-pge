#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py — compila um documento institucional da PGE-MS (HTML) em PDF A4, com
cabeçalho e rodapé institucionais em todas as páginas, capa e contracapa
próprias quando o HTML as declara.

    python scripts/dpge.py build <documento.html> [--modo sobrio|completo] [--conferir]

Por que Playwright e não @page do CSS:
    o Chrome ignora as margin boxes do CSS paginado (@top-center, @bottom-right),
    então cabeçalho e rodapé precisam vir pelos templates do próprio page.pdf().
    Como esses templates não carregam arquivo externo, o logo entra embutido
    em base64.

--conferir rasteriza cada página em PNG dentro de _conferencia/, para inspeção
visual das quebras antes de protocolar. É a etapa que de fato garante o
resultado: CSS de impressão mente com frequência.
"""

import argparse
import base64
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from navegador import abrir as abrir_navegador

RAIZ = Path(__file__).resolve().parent.parent
DESIGN = RAIZ / "assets" / "design-system"
LOGO = DESIGN / "logo-pge.png"
FONTES_DIR = DESIGN / "fonts"

# As folhas do design system. Só são embutidas no caminho com nota de rodapé;
# sem nota, o documento continua carregando por <link>. São casadas com o <link>
# pelo NOME do arquivo, e não pela posição, porque a publicação carrega três
# folhas e o documento simples carrega duas.
FOLHAS = ("tokens.css", "componentes.css", "publicacao.css")

# Polyfill de CSS Paged Media. É ele — e não o Chrome — que implementa
# `float: footnote`. Ver a seção 21 do componentes.css.
PAGED_JS = DESIGN / "vendor" / "paged.min.js"

# --- Geometria da página ------------------------------------------------
# Margens generosas no topo e no pé para acomodar cabeçalho e rodapé sem
# que o conteúdo passe por baixo deles.
MARGENS = {"top": "31mm", "bottom": "19mm", "left": "25mm", "right": "25mm"}

MM = 3.779527559  # 1 mm em px CSS a 96 dpi (templates do Chrome usam px)

# --- Paletas -----------------------------------------------------------
# Cada uma define os dois papéis de cor: `acento` (numeração de seção,
# filetes, marcadores, rótulos) e `citacao` (eixo de precedentes). O marinho
# do texto e a família de cinzas não mudam: são a base institucional.
PALETAS = {
    # Padrão. Marinho estrutural; o laranja fica reservado ao papel --destaque
    # do CSS e não aparece em cabeçalho, filete ou numeração.
    "institucional": dict(
        acento="#294964", acento_escuro="#294964", acento_claro="#8FA9BC",
        acento_palido="#C3D2DD", acento_fundo="#F4F7FA",
        citacao="#366586", citacao_escuro="#294964", citacao_claro="#9DB4C6",
        citacao_fundo="#F4F7FA",
    ),
    # Verde-água da própria tabela da PGE. Sai o laranja sem sair da marca.
    "agua": dict(
        acento="#51A8B1", acento_escuro="#3C7B82", acento_claro="#A9D4D8",
        acento_palido="#C7E3E6", acento_fundo="#F2FAFB",
        citacao="#366586", citacao_escuro="#294964", citacao_claro="#9DB4C6",
        citacao_fundo="#F4F7FA",
    ),
    # Marinho sobre marinho. O mais sóbrio dos quatro, quase sem cor.
    "marinho": dict(
        acento="#366586", acento_escuro="#294964", acento_claro="#B6C9D8",
        acento_palido="#CFDCE6", acento_fundo="#F4F7FA",
        citacao="#51A8B1", citacao_escuro="#3C7B82", citacao_claro="#A9D4D8",
        citacao_fundo="#F3FAFB",
    ),
    # Bordô. Contraste quente com o marinho, de tradição forense.
    "bordo": dict(
        acento="#8A3A48", acento_escuro="#6E2E3A", acento_claro="#C08A94",
        acento_palido="#DCBCC2", acento_fundo="#FBF5F6",
        citacao="#51A8B1", citacao_escuro="#3C7B82", citacao_claro="#A9D4D8",
        citacao_fundo="#F3FAFB",
    ),
    # Bronze. O calor do laranja sem a estridência dele.
    "bronze": dict(
        acento="#8A6E3B", acento_escuro="#6E5730", acento_claro="#C4A97A",
        acento_palido="#DBC79E", acento_fundo="#FAF7F0",
        citacao="#51A8B1", citacao_escuro="#3C7B82", citacao_claro="#A9D4D8",
        citacao_fundo="#F3FAFB",
    ),
    # A original, mantida só para comparação.
    "laranja": dict(
        acento="#F58634", acento_escuro="#C16C2F", acento_claro="#FAB370",
        acento_palido="#FDC685", acento_fundo="#FFF9F2",
        citacao="#51A8B1", citacao_escuro="#3C7B82", citacao_claro="#A9D4D8",
        citacao_fundo="#F3FAFB",
    ),
}


# --- Escala tipográfica ------------------------------------------------
# Os corpos do tokens.css, para poderem ser escalados em bloco. Mudar só o
# --t-corpo deixaria rótulo, citação e apoio no tamanho antigo e desmontaria
# a hierarquia; a régua do livro é decidir o corpo do texto primeiro e
# relacionar todo o resto a ele.
ESCALA = {
    "t-corpo": 12.0, "t-corpo-alt": 11.1, "t-secao": 13.3,
    "t-subsecao": 12.0, "t-citacao": 10.9, "t-rotulo": 8.2,
    "t-apoio": 9.6, "t-capa-titulo": 25.6,
}
CORPO_BASE = ESCALA["t-corpo"]

# Fontes serifadas da lista A de Butterick que existem no Windows, com as
# quatro variantes que a peça usa (romano, negrito, itálico, negrito-itálico).
# Nomeadas aqui para não depender de o usuário lembrar a grafia exata.
FONTES = {
    "montserrat": "'Montserrat VL', 'Montserrat', 'Segoe UI', Arial, sans-serif",
    "palatino":   "'Palatino Linotype', 'Book Antiqua', Palatino, serif",
    "calisto":    "'Calisto MT', serif",
    "schoolbook": "'Century Schoolbook', 'New Century Schlbk', serif",
    "garamond":   "'Garamond', 'EB Garamond', serif",
    "goudy":      "'Goudy Old Style', serif",
    "bell":       "'Bell MT', serif",
    "antiqua":    "'Book Antiqua', Palatino, serif",
}


def css_escala(corpo: float) -> str:
    """Escala toda a régua de corpos na proporção do novo corpo do texto."""
    k = corpo / CORPO_BASE
    regras = [f"--{nome}:{valor * k:.2f}pt" for nome, valor in ESCALA.items()]
    # O --k governa os corpos que vivem dentro dos componentes, fora da régua.
    regras.append(f"--k:{k:.4f}")
    return ":root{" + ";".join(regras) + "}"


def css_paleta(nome: str) -> str:
    p = PALETAS[nome]
    return ":root{" + ";".join(
        f"--{k.replace('_', '-')}:{v}" for k, v in p.items()
    ) + "}"


def px(mm: float) -> str:
    return f"{mm * MM:.1f}px"


def logo_data_uri() -> str:
    dados = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{dados}"


def ler_meta(html: str, nome: str, padrao: str = "") -> str:
    # Meta dentro de comentário não vale: o modelo deixa exemplos comentados.
    html = RX_COMENTARIO.sub("", html)
    m = re.search(
        r'<meta\s+name=["\']' + re.escape(nome) + r'["\']\s+content=["\'](.*?)["\']',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else padrao


def cabecalho(tipo_peca: str, orgao: str, acento: str, acento_escuro: str) -> str:
    """Cabeçalho institucional repetido em todas as páginas."""
    return f"""
    <div style="
        -webkit-print-color-adjust: exact; print-color-adjust: exact;
        width: 100%; margin: 0;
        padding: {px(9)} {px(20)} 0 {px(25)};
        font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
        color: #294964; box-sizing: border-box;">
      <div style="display: flex; align-items: flex-end; justify-content: space-between;">
        <img src="{logo_data_uri()}" style="height: {px(11)}; width: auto; display: block;">
        <div style="text-align: right; line-height: 1.25;">
          <div style="font-size: {px(2.5)}; letter-spacing: 0.16em;
                      text-transform: uppercase; font-weight: 600; color: {acento_escuro};">
            {tipo_peca}
          </div>
          <div style="font-size: {px(2.3)}; letter-spacing: 0.04em;
                      color: #6E7C88; font-weight: 500; margin-top: {px(0.8)};">
            {orgao}
          </div>
        </div>
      </div>
      <div style="margin-top: {px(3)}; height: {px(0.45)}; background: #D2D3D5;
                  position: relative;">
        <div style="position: absolute; left: 0; top: 0; width: {px(26)};
                    height: {px(0.45)}; background: {acento};"></div>
      </div>
    </div>
    """


def rodape(rotulo: str, referencia: str, acento: str) -> str:
    """Rodapé com a referência do documento e a paginação, em todas as páginas.

    O rótulo é "Processo n." nas peças processuais, mas o mesmo design system
    serve a documento que não tem processo (ofício, solicitação técnica). Nesse
    caso, `<meta name="vl-rodape-rotulo">` troca o rótulo, e omitir
    `vl-processo` deixa o rodapé apenas com a paginação."""
    referencia_html = (
        f"""<span style="text-transform: uppercase;">
          {rotulo} <span style="color: #294964; font-weight: 600;">{referencia}</span>
        </span>"""
        if referencia
        else "<span></span>"
    )
    return f"""
    <div style="
        -webkit-print-color-adjust: exact; print-color-adjust: exact;
        width: 100%; margin: 0;
        padding: 0 {px(20)} 0 {px(25)};
        font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
        box-sizing: border-box;">
      <div style="height: {px(0.35)}; background: #D2D3D5; margin-bottom: {px(2.6)};
                  position: relative;">
        <div style="position: absolute; right: 0; top: 0; width: {px(14)};
                    height: {px(0.35)}; background: {acento};"></div>
      </div>
      <div style="display: flex; align-items: baseline; justify-content: space-between;
                  font-size: {px(2.35)}; letter-spacing: 0.08em; color: #6E7C88;
                  font-weight: 500;">
        {referencia_html}
        <span style="text-transform: uppercase;">
          Pág. <span class="pageNumber" style="color: #294964; font-weight: 700;"></span>
          de <span class="totalPages" style="color: #294964; font-weight: 700;"></span>
        </span>
      </div>
    </div>
    """


def juntar(partes: list) -> bytes:
    """Emenda as partes na ordem: capa, corpo, contracapa. A capa e a contracapa
    ficam sem número; a paginação do rodapé conta só as páginas do corpo, que é
    a convenção de manual impresso."""
    import pymupdf as fitz

    doc = fitz.open("pdf", partes[0])
    for parte in partes[1:]:
        resto = fitz.open("pdf", parte)
        doc.insert_pdf(resto)
        resto.close()
    dados = doc.tobytes()
    doc.close()
    return dados


def ajustar_metadados(dados: bytes, titulo: str, autor: str) -> bytes:
    """Grava título e autor no PDF, para o leitor mostrar o nome do documento
    e não o do arquivo temporário."""
    import pymupdf as fitz

    doc = fitz.open("pdf", dados)
    meta = doc.metadata or {}
    meta.update({"title": titulo, "author": autor, "creator": "diagramacao-pge"})
    doc.set_metadata(meta)
    saida = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return saida


# Caminhos do design system dentro do HTML. O documento pode morar em qualquer
# pasta; ele aponta para o design system com `@ds/tokens.css` (ou com o caminho
# relativo antigo `../../design-system/`), e o build troca pelo caminho absoluto
# da cópia que viaja com a skill.
RX_DS = re.compile(
    r"""(?P<attr>(?:href|src)=["'])(?:\.\./)*(?:@ds|design-system)/(?P<resto>[^"']+)""")


def resolver_design_system(html: str) -> str:
    base = DESIGN.resolve().as_uri()
    return RX_DS.sub(lambda m: f"{m.group('attr')}{base}/{m.group('resto')}", html)


def gravar(destino: Path, dados: bytes) -> Path:
    """Grava o PDF. Se o arquivo estiver aberto no Acrobat, o Windows trava a
    escrita; nesse caso grava ao lado, com sufixo, em vez de perder o build."""
    try:
        destino.write_bytes(dados)
        return destino
    except PermissionError:
        alternativo = destino.with_name(destino.stem + "-NOVO" + destino.suffix)
        alternativo.write_bytes(dados)
        print(
            f"  AVISO: {destino.name} está aberto em outro programa e não pôde ser\n"
            f"         sobrescrito. Gravei em {alternativo.name}. Feche o visualizador\n"
            f"         e renomeie, ou rode de novo.",
        )
        return alternativo


# ---------------------------------------------------------------------------
# Nota de rodapé: o caminho com Paged.js
#
# Só entra em ação quando o documento tem `.nota-rodape`. Documento sem nota
# imprime pelo caminho de sempre, byte a byte — o polyfill repagina o DOM
# inteiro e não vale correr esse risco onde ele não resolve nada.
# ---------------------------------------------------------------------------

# Comentario HTML. Sai da conta ANTES de procurar a classe: o modelo traz um
# exemplo de nota comentado, e uma busca por substring crua ligaria o paginador
# em toda peca nova por causa dele - repaginando documento que nao tem nota.
RX_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
# So a classe DE VERDADE conta: `class=` dentro de uma tag, seguido do nome.
# Prosa que apenas mencione `nota-rodape` nao liga o paginador.
RX_NOTA_RODAPE = re.compile("class=[^>]*nota-rodape")
RX_CONTRACAPA = re.compile(r"<section[^>]*class=[\"'][^\"']*\bcontracapa\b")


def tem_nota_rodape(html: str) -> bool:
    return bool(RX_NOTA_RODAPE.search(RX_COMENTARIO.sub("", html)))


def css_pagina() -> str:
    """O `@page` que o Paged.js lê para paginar.

    Tem de repetir as margens de MARGENS, e repete DERIVANDO delas: com o
    polyfill em cena, o `@page` do CSS VENCE as margens passadas ao Chromium.
    O próprio Paged.js emite `@page{margin:0}` ao paginar; sem esta regra o
    corpo passa a nascer na borda do papel e invade o cabeçalho, que continua
    sendo desenhado por cima. Duas listas de margem escritas à mão divergiriam
    na primeira emenda, e o sintoma seria esse — nunca uma exceção.
    """
    m = MARGENS
    return ("@page{size:210mm 297mm;"
            f"margin:{m['top']} {m['right']} {m['bottom']} {m['left']}}}")


def folha_embutida(nome: str) -> str:
    """O texto de uma folha, com as URLs de fonte reescritas para absolutas.

    O Paged.js lê as folhas do documento por `fetch()`, e num documento aberto
    por `file://` o Chrome RECUSA todo fetch de `file://`: a folha referenciada
    por <link> chegaria VAZIA ao polyfill e o documento sairia sem estilo
    nenhum. Embutida, ele lê o `textContent` e não há rede envolvida.

    A reescrita das fontes não é detalhe: embutido no HTML, `url('fonts/X.ttf')`
    passa a resolver a partir da pasta do documento, onde não há pasta `fonts`. A
    fonte falharia em silêncio, o Chrome cairia no fallback e a paginação
    inteira mudaria sem uma linha de erro. Por isso cada arquivo é conferido.
    """
    texto = (DESIGN / nome).read_text(encoding="utf-8")
    for arquivo in sorted(FONTES_DIR.glob("*.ttf")):
        alvo = f"fonts/{arquivo.name}"
        if alvo in texto:
            texto = texto.replace(alvo, arquivo.resolve().as_uri())
    faltando = re.findall(r"url\(['\"](fonts/[^'\"]+)", texto)
    if faltando:
        raise FileNotFoundError(
            f"{nome} referencia fonte que nao existe em {FONTES_DIR}: "
            f"{', '.join(faltando)}. Sem o arquivo o Chrome cai no fallback e "
            f"a paginacao muda sem aviso."
        )
    return texto


# Roda o Paged.js e DEVOLVE o desfecho, em vez de deixar a página seguir como
# se nada tivesse acontecido. `preview()` é uma promessa: aguardá-la é a única
# espera determinística — dormir n milissegundos é aposta.
PAGED_BOOTSTRAP = """
async () => {
  const M = window.PagedModule;
  if (!M || !M.Previewer) {
    return {erro: "paged.min.js nao carregou (window.PagedModule ausente)"};
  }
  try {
    const fluxo = await new M.Previewer().preview();
    return {paginas: fluxo && fluxo.total,
            divs: document.querySelectorAll(".pagedjs_page").length};
  } catch (e) {
    return {erro: String((e && e.message) || e)};
  }
}
"""


class PaginacaoFalhou(RuntimeError):
    """O Paged.js nao concluiu a paginacao.

    Levantar é deliberado. Sem o polyfill o Chrome ignora `float: footnote` e
    o texto da nota sai DENTRO DO PARÁGRAFO, no meio da frase: um PDF errado
    com cara de certo, que ninguém revisando por cima perceberia. Não gerar
    nada é o desfecho seguro.
    """


def preparar_paginacao(pagina, caminho_html: Path) -> None:
    """Embute as folhas, declara o `@page` e roda o polyfill."""
    if not PAGED_JS.is_file():
        raise FileNotFoundError(
            f"paged.min.js ausente: {PAGED_JS}. Sem ele a nota de rodape sai "
            f"dentro do paragrafo."
        )

    # O `@page` entra ANTES das folhas de propósito: no Paged.js as notas do
    # `@page` são ATRIBUÍDAS ao ÚLTIMO `@page` do documento, não fundidas com
    # os anteriores. Declarado depois, ele apagaria o `@footnote` da seção 21
    # e a área de notas sairia sem filete nem respiro, em silêncio.
    pagina.evaluate(
        """([regraPagina, folhas]) => {
            const head = document.head;
            const links = [...head.querySelectorAll('link[rel="stylesheet"]')];

            const est = document.createElement('style');
            est.textContent = regraPagina;
            head.insertBefore(est, links[0] || head.firstChild);

            // Cada <link> vira <style> NO MESMO LUGAR: a ordem de carga e o
            // que decide o desempate entre regras de mesma especificidade, e
            // reordenar aqui mudaria qual vence.
            links.forEach((link, i) => {
                const folha = document.createElement('style');
                const nome = (link.getAttribute('href') || '').split('/').pop();
                if (!(nome in folhas)) return;  // folha de fora: segue como <link>
                folha.textContent = folhas[nome];
                link.replaceWith(folha);
            });
        }""",
        [css_pagina(), {nome: folha_embutida(nome) for nome in FOLHAS
                        if (DESIGN / nome).is_file()}],
    )

    pagina.add_script_tag(path=str(PAGED_JS))
    desfecho = pagina.evaluate(PAGED_BOOTSTRAP)

    if desfecho.get("erro"):
        raise PaginacaoFalhou(f"Paged.js falhou: {desfecho['erro']}")
    # O sucesso da promessa não basta: quem prova a paginação é o DOM. Sem
    # `div.pagedjs_page` não houve paginação, e a nota não foi para o pé.
    if not desfecho.get("divs"):
        raise PaginacaoFalhou(
            "Paged.js terminou sem produzir nenhuma div.pagedjs_page; a nota "
            f"nao teria ido para o pe da pagina ({caminho_html.name})."
        )
    print(f"  notas de rodape: paginado pelo Paged.js "
          f"({desfecho['divs']} paginas)")


def compilar(caminho_html: Path, *args, **kwargs) -> Path:
    """Compila e, haja o que houver, apaga o HTML temporário."""
    try:
        return _compilar(caminho_html, *args, **kwargs)
    finally:
        caminho_html.with_name(f".dpge-{caminho_html.stem}.tmp.html").unlink(
            missing_ok=True)


def avisar_estouros(pagina) -> None:
    """Avisa de tabela, gráfico, figura ou quadro mais largo que a coluna.

    O Chromium não imprime o que passa da margem direita: a parte que sobra
    some do PDF sem erro, e uma coluna inteira de tabela pode desaparecer. A
    medida é feita com a largura útil do texto (160 mm, 605 px) e a mídia de
    impressão, e a página volta ao tamanho de antes."""
    anterior = pagina.viewport_size
    pagina.set_viewport_size({"width": 605, "height": 900})
    pagina.emulate_media(media="print")
    medidas = pagina.evaluate(
        """() => {
            const largura = document.documentElement.clientWidth;
            const achados = [];
            for (const el of document.querySelectorAll(
                    'table, .grafico, figure, img, pre, .sintese, .modelo, .confronto')) {
                if (el.closest('.capa-manual, .contracapa, .cm-topo')) continue;
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.right > largura + 1.5) {
                    achados.push([el.tagName.toLowerCase(),
                                  (el.innerText || el.alt || '').trim().replace(/\\s+/g, ' ').slice(0, 40),
                                  Math.round((r.right - largura) * 25.4 / 96)]);
                }
            }
            return achados;
        }""")
    pagina.emulate_media(media=None)
    if anterior:
        pagina.set_viewport_size(anterior)
    for tag, trecho, mm in medidas[:6]:
        print(f"  AVISO: <{tag}> passa {mm} mm da margem direita e será cortado no PDF: "
              f"\"{trecho}\". Reduza colunas, abrevie ou divida a tabela.")


def _compilar(caminho_html: Path, modo: str, conferir: bool,
             entrelinha=None, esp_paragrafo=None, sufixo="", paleta=None,
             corpo=None, fonte=None, texto=None, estrutura=None,
             saida=None, permitir_pendencias=False) -> Path:
    html = caminho_html.read_text(encoding="utf-8")

    # Marcadores deixados pelo modelo. PDF com "[PREENCHER: ...]" impresso é
    # o erro mais fácil de cometer e o pior de achar depois da distribuição.
    visivel = RX_COMENTARIO.sub("", html)
    pendentes = re.findall(r"\[PREENCHER[^\]]*\]", visivel)
    if pendentes and not permitir_pendencias:
        lista = "\n".join(f"  - {p}" for p in dict.fromkeys(pendentes))
        raise SystemExit(
            f"{len(pendentes)} marcador(es) [PREENCHER] ainda no documento:\n{lista}\n"
            "Preencha ou apague cada um. (--permitir-pendencias compila assim "
            "mesmo, só para teste.)")
    if pendentes and permitir_pendencias:
        print(f"  AVISO: {len(pendentes)} marcador(es) [PREENCHER] no PDF "
              "(--permitir-pendencias): é versão de teste, não distribua.")
    por_conferir = re.findall(r"\[CONFERIR[^\]]*\]", visivel)
    if por_conferir:
        print(f"  AVISO: {len(por_conferir)} marcador(es) [CONFERIR] no texto; "
              "confirme a informação antes de distribuir.")

    processo = ler_meta(html, "vl-processo", "")
    # Capa própria: o design system nasceu para peça processual, cujo modo
    # completo traz a capa dentro do fluxo, com cabeçalho e rodapé por cima.
    # Manual e apostila precisam de capa limpa, sem cabeçalho nem paginação.
    # `<meta name="vl-capa" content="propria">` liga o caminho de dois
    # renderizadores: um só para a capa, sem margem e sem templates, e outro
    # para o corpo, que é onde a paginação começa a contar.
    capa_propria = ler_meta(html, "vl-capa", "").lower() == "propria"
    rotulo_rodape = ler_meta(html, "vl-rodape-rotulo", "Documento n.")
    tipo_peca = ler_meta(html, "vl-peca", "Documento institucional")
    # `vl-tipo: peca` liga a tipografia da seção 20 do componentes.css
    # (corpo serifado, recuo de parágrafo, título justificado). Sem a meta,
    # documento institucional sai exatamente como saía antes.
    eh_peca = ler_meta(html, "vl-tipo", "").lower() == "peca"
    notas = tem_nota_rodape(html)
    # Contracapa: presença do elemento, sem meta. Comentário não conta, para o
    # exemplo comentado do modelo não ligar a passada em documento que não a tem.
    contracapa = bool(RX_CONTRACAPA.search(RX_COMENTARIO.sub("", html)))
    titulo_pdf = re.sub(r"<[^>]+>", "", ler_meta(html, "vl-titulo", "") or
                        (re.search(r"<title>(.*?)</title>", html, re.S) or
                         [None, caminho_html.stem])[1])
    titulo_pdf = re.sub(r"\s+", " ", titulo_pdf.replace("&nbsp;", " ")).strip()

    if notas and capa_propria:
        # A capa própria imprime numa segunda passada, com margem zero, e
        # o Paged.js já compôs as páginas com a margem do `@page`. Falhar
        # aqui é melhor que entregar um PDF com a capa fora de esquadro.
        raise SystemExit(
            "vl-capa=propria e nota de rodape nao se combinam: a capa "
            "imprime com margem zero e o paginador ja compos as paginas. "
            "Tire a capa propria ou troque a nota por texto no fluxo.")
    orgao = ler_meta(html, "vl-orgao", "Procuradoria-Geral do Estado de Mato Grosso do Sul")

    cores = PALETAS[paleta or "institucional"]
    saida = saida or caminho_html.parent / f"{caminho_html.stem}-{modo}{sufixo}.pdf"

    # O HTML que o navegador abre é uma cópia ao lado do original, com os
    # caminhos do design system trocados pelos da skill. Fica na mesma pasta
    # para que as imagens do documento (capa, figuras) continuem resolvendo
    # pelo caminho relativo; some ao fim do build.
    temporario = caminho_html.with_name(f".dpge-{caminho_html.stem}.tmp.html")
    temporario.write_text(resolver_design_system(html), encoding="utf-8")

    with sync_playwright() as p:
        navegador, nome_navegador = abrir_navegador(p)
        pagina = navegador.new_page()
        pagina.goto(temporario.resolve().as_uri(), wait_until="load")

        # O modo é uma classe no <body>: mesmo HTML, duas saídas.
        pagina.evaluate(
            """([modo, ehPeca]) => {
                document.body.classList.remove('modo-sobrio', 'modo-completo');
                document.body.classList.add('modo-' + modo);
                document.body.classList.toggle('doc-peca', ehPeca);
            }""",
            [modo, eh_peca],
        )
        # Paleta e ritmo do texto, sem tocar no CSS do projeto
        if paleta:
            pagina.add_style_tag(content=css_paleta(paleta))
        if corpo:
            pagina.add_style_tag(content=css_escala(corpo))
        regras = []
        if entrelinha:
            regras.append(f"--lh-corpo:{entrelinha}")
        if esp_paragrafo:
            regras.append(f"--esp-paragrafo:{esp_paragrafo}mm")
        if fonte:
            # Troca as DUAS: na peca o corpo e `--fonte-corpo` e os rotulos sao
            # `--fonte`. Trocar so uma faria o teste comparativo de fontes medir
            # os rotulos e deixar o corpo como estava.
            familia = FONTES.get(fonte, fonte)
            regras.append("--fonte:" + familia)
            regras.append("--fonte-corpo:" + familia)
        if texto:
            regras.append(f"--texto:{texto}")
        if estrutura:
            # Título, numeração, filete, rótulo, cabeçalho de tabela e tarja.
            regras.append(f"--marinho:{estrutura}")
        if regras:
            # `:root` sozinho NAO alcanca a peca, e o motivo nao e ordem nem
            # especificidade: `.doc-peca` redeclara `--fonte` no proprio
            # <body>, e declaracao local vence valor herdado do <html>. Sem o
            # segundo seletor, `--fonte` e `--texto` viravam no-op silencioso
            # em toda peca — justamente nos testes que o guia (references/tipografia.md §9) manda refazer.
            pagina.add_style_tag(
                content=":root,.doc-peca{" + ";".join(regras) + "}")

        pagina.evaluate("document.fonts.ready")
        pagina.wait_for_timeout(400)
        avisar_estouros(pagina)

        # Depois das injeções de paleta e escala (o polyfill congela o
        # layout ao paginar; estilo acrescentado depois não é relido) e
        # antes de qualquer `pdf()`.
        if notas:
            preparar_paginacao(pagina, caminho_html)
            pagina.evaluate("document.fonts.ready")
            pagina.wait_for_timeout(200)

        capa_bytes = None
        if capa_propria:
            # A classe .so-capa esconde tudo o que não é a capa; a .sem-capa
            # faz o inverso. As duas regras vivem no CSS do próprio documento,
            # porque cada capa tem geometria própria.
            pagina.evaluate("document.body.classList.add('so-capa')")
            pagina.wait_for_timeout(120)
            capa_bytes = pagina.pdf(
                format="A4",
                print_background=True,
                display_header_footer=False,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                prefer_css_page_size=False,
            )
            pagina.evaluate("""() => {
                document.body.classList.remove('so-capa');
                document.body.classList.add('sem-capa');
            }""")
            pagina.wait_for_timeout(120)

        dados = pagina.pdf(
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=cabecalho(tipo_peca, orgao, cores["acento"],
                                      cores["acento_escuro"]),
            footer_template=rodape(rotulo_rodape, processo, cores["acento"]),
            margin=MARGENS,
            prefer_css_page_size=False,
        )

        contracapa_bytes = None
        if contracapa:
            # Mesma ideia da capa: página inteira, sem margem e sem templates.
            pagina.evaluate("""() => {
                document.body.classList.remove('so-capa', 'sem-capa');
                document.body.classList.add('so-contracapa');
            }""")
            pagina.wait_for_timeout(120)
            contracapa_bytes = pagina.pdf(
                format="A4",
                print_background=True,
                display_header_footer=False,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                prefer_css_page_size=False,
            )
        navegador.close()

    partes = [b for b in (capa_bytes, dados, contracapa_bytes) if b]
    if len(partes) > 1:
        dados = juntar(partes)
    dados = ajustar_metadados(dados, titulo_pdf, orgao)

    saida = gravar(saida, dados)

    if conferir:
        rasterizar(saida, modo)

    return saida


def rasterizar(pdf: Path, modo: str) -> None:
    """Gera um PNG por página para conferência visual das quebras."""
    import pymupdf as fitz

    destino = pdf.parent / "_conferencia"
    destino.mkdir(exist_ok=True)
    for antigo in destino.glob(f"{modo}-p*.png"):
        antigo.unlink()

    doc = fitz.open(pdf)
    for i, pagina in enumerate(doc, start=1):
        pix = pagina.get_pixmap(dpi=110)
        pix.save(destino / f"{modo}-p{i:02d}.png")
    print(f"  conferência: {len(doc)} páginas em {destino}")
    doc.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path, help="caminho do documento .html")
    ap.add_argument(
        "--modo",
        choices=["sobrio", "completo", "ambos"],
        default="sobrio",
        help="sobrio = só tipografia e quadros (padrão, serve a manual e "
             "apostila); completo = com capa no fluxo, linha do tempo e "
             "gráficos, para documento curto",
    )
    ap.add_argument(
        "--conferir",
        action="store_true",
        help="rasteriza cada página em PNG para inspeção das quebras",
    )
    ap.add_argument("--entrelinha", type=float, default=None,
                    help="entrelinha do corpo (padrão do CSS: 1.22)")
    ap.add_argument("--espaco-paragrafo", type=float, default=None,
                    dest="espaco_paragrafo",
                    help="espaço entre parágrafos em mm (padrão: 3)")
    ap.add_argument("--paleta", choices=sorted(PALETAS), default=None,
                    help="cor de acento; padrão é a institucional do tokens.css")
    ap.add_argument("--corpo", type=float, default=None,
                    help="corpo do texto em pt (padrão: 12). Escala toda a "
                         "régua de tamanhos na mesma proporção")
    ap.add_argument("--fonte", default=None,
                    help="família do texto: " + ", ".join(sorted(FONTES))
                         + ", ou uma lista CSS completa entre aspas")
    ap.add_argument("--texto", default=None,
                    help="hex do texto de leitura (padrão: #000000)")
    ap.add_argument("--estrutura", default=None,
                    help="hex do marinho de títulos e moldura (padrão: #152B3F)")
    ap.add_argument("--permitir-pendencias", action="store_true",
                    dest="permitir_pendencias",
                    help="compila mesmo com [PREENCHER] no texto (só para teste)")
    ap.add_argument("--saida", type=Path, default=None,
                    help="caminho do PDF final (só com um modo por vez)")
    ap.add_argument("--sufixo", default="",
                    help="sufixo no nome do PDF, para gerar variantes lado a lado")
    args = ap.parse_args()

    # O console do Windows abre em cp1252 e estoura em acento fora dele.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    if not args.html.exists():
        print(f"erro: não encontrei {args.html}", file=sys.stderr)
        return 1
    if not LOGO.exists():
        print(f"erro: não encontrei o logo em {LOGO}", file=sys.stderr)
        return 1

    if args.saida and not args.saida.is_absolute() and args.saida.parent == Path("."):
        args.saida = args.html.resolve().parent / args.saida.name
    modos = ["sobrio", "completo"] if args.modo == "ambos" else [args.modo]
    for modo in modos:
        saida = compilar(args.html, modo, args.conferir,
                         args.entrelinha, args.espaco_paragrafo, args.sufixo,
                         args.paleta, args.corpo, args.fonte, args.texto,
                         args.estrutura,
                         args.saida if len(modos) == 1 else None,
                         args.permitir_pendencias)
        import pymupdf as fitz
        d = fitz.open(saida); n = len(d); d.close()
        print(f"gerado: {saida}  ({n} páginas)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
