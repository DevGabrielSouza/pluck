# 0006. Uma instância por usuário

Status: aceita

## Contexto

Abrir o Pluck duas vezes criava duas filas gravando o mesmo `history.json`. A última a fechar sobrescrevia a outra, e os mesmos downloads podiam rodar em dobro.

## Decisão

O socket (`pluck.sock`) e um lock (`pluck.lock`) ficam em `XDG_RUNTIME_DIR`, que é do usuário e tem modo 0700. Ao abrir, o app pega o lock com `QLockFile` e, segurando o lock, tenta falar com o socket:

- se alguém responde, envia `activate` e sai; a janela que já existe vem para a frente;
- se ninguém responde, remove um socket órfão, cria o `QLocalServer` com `UserAccessOption` e solta o lock.

O lock serializa as aberturas simultâneas. Sem ele, duas aberturas podiam falhar ao conectar ao mesmo tempo e a segunda apagava o socket da primeira; com 6 processos simultâneos, isso gerou mais de uma instância principal em 3 de 5 rodadas.

Se o lock não sair em 3 s ou o `listen` falhar, o app abre mesmo assim e registra um aviso. Recusar abrir por causa de um arquivo de controle seria pior que o risco de duas janelas nessa situação anormal.

## Consequências

- Um único dono do histórico; `test_simultaneous_launches_elect_a_single_instance` sobe 6 processos ao mesmo tempo e exige exatamente uma instância principal.
- Outro usuário não alcança o socket nem consegue ocupar o nome antes, como seria possível no `/tmp`.
- No Wayland, trazer a janela para a frente depende do compositor; o KDE pode só destacar a janela na barra de tarefas.
