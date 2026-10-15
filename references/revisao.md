# Revisão ortográfica e gramatical (etapa prévia)

Toda diagramação começa por esta revisão, antes de montar capa, sumário e corpo. Texto com erro diagramado vira PDF com erro, e depois de impresso não há como corrigir. A revisão é do texto; o estilo do autor não se mexe.

A única dispensa é o usuário dizer que o texto já passou por revisão profissional. Nesse caso registre a dispensa no relatório final e siga. Os textos que a própria skill redigir (descritor da capa, caixas de síntese) passam pela mesma revisão.

## Como fazer

1. Converta o texto para HTML (`converter`) e guarde uma cópia intocada: `corpo-original.html`. É a base da comparação.
2. Releia `corpo.html` bloco a bloco e corrija **só o texto**, editando o conteúdo das tags sem trocar tag, classe nem estrutura.
3. Compare: `<dpge> revisar corpo-original.html corpo.html --saida revisao.md`. O relatório lista cada troca (`[-tirado-]`, `{+entrou+}`) e marca com ATENÇÃO o que não deveria mudar sem conferência.
4. Mostre ao usuário o resumo (quantos blocos, o que é recorrente) e os itens de ATENÇÃO. Item recusado volta ao original. Só depois siga para a diagramação.

O comando sai com código 1 quando há ATENÇÃO. Isso não é falha: é o pedido de conferência.

## O que corrigir

- Ortografia e acentuação, pelo Acordo Ortográfico em vigor (hífen, trema, acento diferencial).
- Concordância verbal e nominal, regência, crase, colocação pronominal.
- Pontuação: vírgula entre sujeito e verbo, vírgula faltando em oração adverbial deslocada, ponto e vírgula mal usado.
- Palavras trocadas ou repetidas ("a a", "de de"), digitação, maiúscula e minúscula (cargos, órgãos, meses e dias da semana em minúscula).
- Uniformidade: a mesma sigla ou expressão escrita de um jeito só ao longo do texto (a forma que o próprio documento já mais usa).

## O que não mexer

- **Citação literal** (entre aspas, em bloco, ementa, trecho de lei). Se tiver erro, é do original: deixe como está e liste para o usuário decidir, com `[sic]` só se ele pedir.
- **Número, data, valor, artigo, norma, número de processo.** Se parecer errado (ex.: "art. 5" onde o contexto pede outro), não corrija: marque `[CONFERIR]` no texto e liste.
- **Nome próprio, cargo, sigla** e termo técnico da área. Na dúvida, pergunte.
- **Estilo e voz do autor.** Frase longa, ordem das palavras e escolha de termo não são erro. Sugestão de estilo vai numa lista à parte, sem aplicar sem o aval do usuário.
- **Conteúdo.** Nunca acrescentar, tirar nem inverter sentido. Se a correção muda o sentido, é pergunta.

A tipografia (aspas curvas, espaço depois de `art.`, reticências) não é desta etapa: é do `checar --corrigir`, que roda depois.

## Entrega ao usuário

No relatório final: quantos blocos foram alterados, os erros mais frequentes (dois ou três exemplos), os itens de ATENÇÃO e como foram decididos, e a lista de sugestões de estilo não aplicadas. O `revisao.md` fica ao lado do documento.
