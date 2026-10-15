#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dpge.py, ponto de entrada único da skill diagramacao-pge.

    dpge setup                  prepara o ambiente (uma vez)
    dpge doctor                 confere o que está instalado
    dpge build   <doc.html> ... compila em PDF
    dpge sumario <doc.html> ... acerta o sumário (compila)
    dpge checar  <doc.html> ... confere a tipografia
    dpge converter <arq> ...    .docx ou .md para HTML
    dpge imagem  <subcomando>   prepara imagem de capa
    dpge grafico criar|extrair  gráfico no padrão da PGE; lê gráficos do .docx
    dpge revisar <antes> <depois>  relatório do que a revisão de texto mudou

"dpge" é este arquivo: `python3 scripts/dpge.py` no Mac e no Linux, `dpge.cmd`
(na raiz da skill) no Windows.

Na primeira execução cria um ambiente virtual fora da pasta da skill, instala as
bibliotecas de requirements.txt e, se o computador não tem Edge nem Chrome,
baixa o Chromium. Só usa a biblioteca padrão para isso.

Variáveis de ambiente:
    DPGE_HOME        onde fica o ambiente virtual
    DPGE_PIP_ARGS    argumentos extras do pip, ex.: "--index-url https://espelho/simple"
    DPGE_NAVEGADOR   chromium, chrome ou edge: qual navegador usar primeiro
"""

import os
import shlex
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
REQUISITOS = AQUI / "requirements.txt"
MINIMO = (3, 10)

COMANDOS = {
    "build": "build.py",
    "sumario": "sumario.py",
    "checar": "checar_tipografia.py",
    "converter": "converter.py",
    "imagem": "imagem.py",
    "grafico": "grafico.py",
    "revisar": "revisao.py",
}


def casa() -> Path:
    if os.environ.get("DPGE_HOME"):
        return Path(os.environ["DPGE_HOME"]).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "diagramacao-pge"


def python_do_venv() -> Path:
    venv = casa() / "venv"
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def marca() -> Path:
    return casa() / "pronto.txt"


def assinatura_requisitos() -> str:
    return REQUISITOS.read_text(encoding="utf-8").strip()


def pip_extra() -> list:
    return shlex.split(os.environ.get("DPGE_PIP_ARGS", ""))


def pronto() -> bool:
    py = python_do_venv()
    m = marca()
    return py.is_file() and m.is_file() and m.read_text(encoding="utf-8") == assinatura_requisitos()


def rodar(cmd: list, dica: str = "", **kw) -> None:
    resultado = subprocess.run(cmd, **kw)
    if resultado.returncode != 0:
        if dica:
            print(dica, file=sys.stderr)
        raise SystemExit(f"falhou: {' '.join(map(str, cmd))}")


def ambiente_de_execucao() -> dict:
    return dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def navegador_disponivel(py: Path):
    """Nome do navegador que o Playwright consegue abrir, ou None."""
    r = subprocess.run([str(py), str(AQUI / "navegador.py")], capture_output=True,
                       text=True, env=ambiente_de_execucao())
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None


def preparar(forcar: bool = False) -> Path:
    """Devolve o Python que roda os scripts, preparando o ambiente se preciso."""
    if sys.version_info < MINIMO:
        raise SystemExit(
            f"Python {MINIMO[0]}.{MINIMO[1]} ou mais novo é necessário "
            f"(este é o {sys.version.split()[0]}). Instale em python.org e rode de novo."
        )
    if pronto() and not forcar:
        return python_do_venv()

    pasta = casa()
    pasta.mkdir(parents=True, exist_ok=True)
    py = python_do_venv()
    if forcar or not py.is_file():
        print(f"[1/3] criando ambiente em {pasta / 'venv'}", flush=True)
        rodar([sys.executable, "-m", "venv", "--clear", str(pasta / "venv")])

    print("[2/3] instalando bibliotecas (alguns minutos na primeira vez)", flush=True)
    rodar([str(py), "-m", "pip", "install", "--quiet", *pip_extra(), "-r", str(REQUISITOS)],
          dica=("Não consegui baixar as bibliotecas. Confira a internet ou aponte um "
                "espelho do PyPI com DPGE_PIP_ARGS."))

    print("[3/3] conferindo o navegador que gera o PDF", flush=True)
    nome = navegador_disponivel(py)
    if nome:
        print(f"      vou usar: {nome} (nada para baixar)", flush=True)
    else:
        print("      nenhum Edge ou Chrome encontrado; baixando o Chromium", flush=True)
        rodar([str(py), "-m", "playwright", "install", "chromium"],
              dica="Instale o Microsoft Edge ou o Google Chrome e rode `setup` de novo.")
    marca().write_text(assinatura_requisitos(), encoding="utf-8")
    print("ambiente pronto.", flush=True)
    return py


def doctor() -> int:
    ok = True
    print(f"Python        {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info < MINIMO:
        print(f"  FALTA: Python {MINIMO[0]}.{MINIMO[1]}+")
        ok = False
    print(f"Ambiente      {casa() / 'venv'}  "
          f"{'pronto' if pronto() else 'NÃO preparado (rode: setup)'}")
    ok = ok and pronto()
    if pronto():
        nome = navegador_disponivel(python_do_venv())
        print(f"Navegador     {nome or 'NENHUM (instale o Edge ou o Chrome)'}")
        ok = ok and bool(nome)
    ds = RAIZ / "assets" / "design-system"
    for arq in ("tokens.css", "componentes.css", "publicacao.css", "logo-pge.png",
                "fonts/SourceSans3.ttf", "fonts/Montserrat.ttf", "fonts/SourceSerif4.ttf",
                "vendor/paged.min.js"):
        existe = (ds / arq).is_file()
        ok = ok and existe
        print(f"{'ok ' if existe else 'FALTA'}  assets/design-system/{arq}")
    return 0 if ok else 1


def main(argv: list) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, resto = argv[0], argv[1:]
    if cmd == "setup":
        preparar(forcar="--forcar" in resto)
        return 0
    if cmd == "doctor":
        return doctor()
    if cmd not in COMANDOS:
        print(f"comando desconhecido: {cmd}\n", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        return 2
    py = preparar()
    return subprocess.run([str(py), str(AQUI / COMANDOS[cmd]), *resto],
                          env=ambiente_de_execucao()).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
