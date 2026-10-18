# 0009. Motor de downloads: estados, grupos de processo e saída marcada

Status: aceita. Substitui a tabela de estados da ADR 0004; a regra de que toda mudança passa por `transition()` continua.

## Contexto

A auditoria de 18/10/2026 (`docs/threat-model.md`) mediu o motor com o yt-dlp 2026.08.19 e o ffmpeg reais contra um servidor local:

- cancelar mandava SIGINT só para o yt-dlp e, depois de 3 s, SIGKILL só para ele. Com o downloader ffmpeg, o SIGINT não cancelou (código 0, arquivo completo) e o SIGKILL deixou o ffmpeg órfão gravando na pasta;
- os eventos de pós-processamento saem no stderr, que o app não lia como evento: a etapa nunca aparecia;
- o `vcodec` vindo do site passa quebra de linha para o stdout, e o marcador fixo `PLUCK_FILE ` podia ser forjado;
- um campo `..` usado sozinho como pasta no modelo de nome tira o arquivo da pasta de destino;
- a legenda baixada antes do vídeo contava como stream de peso 1 e levava a barra a 100% antes da hora;
- não havia `resolving`, nem nova tentativa para queda de rede, e a tela dizia "Retomar" sem garantia de retomada.

## Decisão

1. Estados `queued`, `resolving`, `downloading`, `postprocessing`, `completed`, `failed`, `canceled` e `interrupted`, com a tabela em `docs/download-engine.md`. O histórico vai para a versão 2 e lê os nomes da versão 1.
2. Cada processo do yt-dlp roda em sessão própria. Cancelar, matar e recolher sobras usam o grupo inteiro.
3. stdout e stderr num canal só, na ordem. Marcadores com token aleatório por execução. Caminho de arquivo fora da pasta do job é descartado.
4. Campos que formam sozinhos um componente de pasta no modelo de nome passam por `--replace-in-metadata CAMPOS '^[\W_]*$' _`, e o comando fixa `--no-restrict-filenames --no-windows-filenames`. A regex roda antes da sanitização do yt-dlp, que apaga caractere de controle e, no modo restrito, normaliza Unicode e troca letras por `_`; fixar a sanitização é o que torna a regex suficiente. Expressão de campo que não dá para proteger assim (formatação com precisão ou conversão diferente de `s` e `d`, barra dentro de `%()`, `&`, padrão só de pontos) torna o modelo inseguro, e ele volta ao padrão como os outros modelos inseguros.
5. Cancelamento vence qualquer falha, inclusive a de lançamento. Só perde para um processo que já tinha terminado o arquivo com sucesso.
6. Falha transitória ganha até 3 novas tentativas com espera crescente. Duas execuções com a mesma URL não rodam juntas.
7. Progresso monotônico dentro da tentativa; legenda não conta como stream; tempo restante só com velocidade, somando o áudio que falta.
8. Sem pausa. "Tentar de novo" no lugar de "Retomar".
9. Executáveis resolvidos só por entradas absolutas do `PATH`.

## Alternativas descartadas

- Pausa com SIGSTOP: o servidor fecha a conexão parada e a continuação depende de `Range`, que não dá para saber antes. Seria prometer o que o yt-dlp não garante.
- Retomar sozinho ao abrir o app: muda o uso de rede sem o usuário pedir, por exemplo numa conexão limitada. O app continua oferecendo a nova tentativa.
- Juntar `interrupted` a `failed`: fechar o app não é erro, e a tela trata os dois de forma diferente.
- Ler eventos do stdout e do stderr separados: os dois pipes chegam fora de ordem, e um progresso atrasado desfaria `postprocessing`.
- Gravar a capa numa pasta privada com `-o "thumbnail:..."`: o yt-dlp grava a capa primeiro ao lado do arquivo temporário, na pasta de destino. Mover o download inteiro para uma pasta temporária exigiria refazer a ADR 0003, mover entre sistemas de arquivos e baixar de novo o que já existe. Ficou como risco documentado.
- `--no-overwrites`: com ele, o yt-dlp usa como capa o arquivo do usuário que tem o mesmo nome e o embute no vídeo.
- Ignorar a config e os plugins do usuário: quebra uso legítimo, como `--js-runtimes` e provedores de token do YouTube. Quem escreve nesses arquivos já controla a conta.

## Consequências

- `QProcess` passa a exigir Qt 6.6 ou mais novo, por causa de `setUnixProcessParameters`. O mínimo do projeto já é 6.10.
- O QML mudou nos nomes de estado e no filtro `completed`. O `history.json` antigo continua abrindo; o novo não abre direito numa versão anterior do app.
- O ganho de grupo vale também para downloader externo e `--exec` vindos da config do usuário: tudo morre junto com o yt-dlp.
- Quem usa `--restrict-filenames` ou `--windows-filenames` na config e um modelo com campo do site como pasta perde essas opções nesses downloads. Com o modelo padrão nada muda.
- Recolher o grupo depois que o yt-dlp saiu tem uma janela teórica de reuso de PID. O Linux não reaproveita o número enquanto algum membro do grupo existe; o sinal vai logo depois da saída.
