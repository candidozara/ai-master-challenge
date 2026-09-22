## Como rodar

Abra um terminal dentro de `solution/churn_engine`. Não precisa instalar
nada antes -- se for a primeira vez nessa máquina, o próprio comando
instala sozinho o que faltar (só acontece essa vez).

### Forma 1 — menu no terminal

```
python main.py
```

Abre um menu explicando cada opção:

```
1) Rodar com dados de exemplo
   Usa os dados de teste que já vêm no projeto -- é só pra ver o sistema funcionando.

2) Rodar com os meus dados
   Você mostra a pasta com os SEUS arquivos CSV e o sistema gera o diagnóstico com eles.

3) Ver o painel gráfico
   Abre uma tela no navegador com os gráficos do último resultado gerado.

4) Conferir se os relatórios estão corretos
   Confere se os arquivos do último resultado foram gerados sem erro.

5) Sair
```

Digite o número e Enter. Nenhum outro comando pra digitar, nenhum nome de
arquivo pra decorar. A opção 2 te guia, um arquivo por vez.

### Forma 2 — painel gráfico direto

```
python main.py --painel
```

Pula o menu e abre o painel no navegador direto -- pra quando você já
rodou o motor antes (opção 1 ou 2) e só quer ver os gráficos de novo.
Dentro do painel tem uma aba **❓ Como usar** que explica cada gráfico e
cada número.
