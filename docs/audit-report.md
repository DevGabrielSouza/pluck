# Relatório da auditoria

Data: 18/10/2026. Escopo: o repositório inteiro (Python, QML, scripts e testes), na versão 0.1.0.

## Inventário

- 26 arquivos Python, cerca de 2500 linhas; 44 arquivos QML.
- Antes: `ytdlp.py`, `downloads.py` e `progress.py` misturavam regra, comando e Qt; não havia checagem de tipos, lint de QML, auditoria de dependências, CI nem documentação de arquitetura.
- Depois: as camadas `domain`, `ytdlp`, `services` e `app`, com a regra de dependência testada (ADR 0007).

## Problemas encontrados

Severidade: crítico (execução de código ou perda de dados sem ação do usuário), alto, médio, baixo. Esforço: P (horas), M (um dia), G (vários dias).

| # | problema | severidade | impacto | esforço | estado |
|---|---|---|---|---|---|
| 1 | `yt-dlp.conf` na pasta de downloads era carregado como config (`-P` apontava para ela), e `--exec` executa comando | crítico | execução de código | P | corrigido (ADR 0003) |
| 2 | Textos vindos do site eram renderizados como rich text, inclusive `<img>` remoto | alto | rastreamento por IP, imitação da interface | P | corrigido |
| 3 | Modelo de nome aceitava `/`, `~` e `..` | alto | gravação fora da pasta de destino | P | corrigido |
| 4 | "Abrir" abria qualquer arquivo baixado, inclusive `.desktop` e scripts | alto | execução de conteúdo baixado | P | corrigido |
| 5 | Versão mínima do yt-dlp não verificada; versões antigas têm CVEs de escrita de arquivo arbitrário | alto | depende da versão instalada | P | aviso na barra de status e `pip-audit` |
| 6 | URL sem limite de tamanho nem filtro de caractere de controle | médio | argumento malformado para o processo | P | corrigido |
| 7 | Idiomas de legenda iam direto para o argumento | médio | injeção de opção | P | corrigido |
| 8 | `notify-send` recebia o título do vídeo sem `--` e sem escapar markup | médio | opção injetada, markup na notificação | P | corrigido |
| 9 | Detalhe de erro mostrava URL assinada e tokens | médio | vazamento de credencial em tela e captura | P | corrigido (`redact`) |
| 10 | Linha sem quebra no stdout crescia sem limite; linhas `ERROR:` do stderr acumulavam sem teto | médio | consumo de memória | P | corrigido |
| 11 | Histórico gravado na thread da interface; troca atômica sem `fsync` | médio | travada da interface; arquivo vazio ou antigo após queda de energia, conforme o sistema de arquivos | M | corrigido (ADR 0005) |
| 12 | Estado do job mudado por atribuição direta em vários pontos | médio | estado incoerente, progresso velho ao tentar de novo | M | corrigido (ADR 0004) |
| 13 | Pasta de destino relativa no `settings.json` era resolvida contra o diretório de onde o app foi aberto | médio | arquivo salvo em lugar inesperado | P | corrigido: rejeitada nas configurações; job com pasta inválida vai para `error` |
| 14 | Duplicata detectada só pela URL: o mesmo vídeo em áudio era descartado em silêncio | médio | download perdido | P | corrigido |
| 15 | Duas instâncias gravavam o mesmo histórico | médio | perda de histórico, download em dobro | P | corrigido (ADR 0006) |
| 16 | SIGTERM e SIGINT matavam o app sem gravar o estado | médio | histórico perdido no logout | P | corrigido |
| 17 | Controles sem nome e papel acessíveis, linhas da playlist fora do teclado, foco invisível | médio | inutilizável com leitor de tela ou só teclado | M | corrigido |
| 18 | Atalhos ativos com diálogo modal aberto; Enter no diálogo não confirmava o botão focado | baixo | ação acidental | P | corrigido |
| 19 | Texto secundário com contraste 3,91:1 | baixo | abaixo do WCAG AA (4,5:1) | P | corrigido (5,08:1) |
| 20 | Sem aviso quando falta ffmpeg | baixo | download falha no fim, sem explicação prévia | P | corrigido |
| 21 | Thumbnail com `sourceSize` zero decodificava a imagem inteira | baixo | memória | P | corrigido |
| 22 | API depreciada `invalidateRowsFilter` | baixo | quebra em versão futura do Qt | P | corrigido |
| 23 | Sem tipos, sem lint de QML, sem auditoria de dependências, sem CI | médio | regressão sem aviso | M | corrigido |

### Achados da revisão adversarial (fase E)

Revisão do Codex (gpt-5.6-sol, effort `high`) sobre o trabalho inteiro, mais o que apareceu ao reproduzir o CI localmente. Todos foram reproduzidos antes de corrigir, e cada correção tem um teste que falha sem ela.

| # | problema | severidade | origem | estado |
|---|---|---|---|---|
| 24 | Duas aberturas simultâneas viravam duas instâncias principais: a segunda apagava o socket da primeira | alto | Codex | corrigido: `QLockFile` e socket em `XDG_RUNTIME_DIR` (ADR 0006) |
| 25 | Job com pasta inválida reagendava a fila de forma recursiva, e o laço externo iniciava o próximo job de novo (`InvalidTransitionError`) | médio | Codex | corrigido |
| 26 | `urlparse` levanta `ValueError` com `https://[abc` ou host inválido em NFKC, e a exceção escapava do slot | médio | Codex | corrigido |
| 27 | O wheel saía sem QML, ícones e assets; `pip install .` gerava um `pluck` que não abria | médio | Codex | corrigido |
| 28 | Botões do `Stepper` sem nome para leitor de tela | baixo | Codex | corrigido |
| 29 | `Keys` anexado ao `Popup` do diálogo de confirmação não funciona (Popup não é Item): Enter não fazia nada | baixo | Qt do PyPI | corrigido; o Qt do Fedora não emite o aviso |
| 30 | O smoke de renderização ignorava avisos de QML sem `.qml:` na mensagem | baixo | própria | agora exige stderr vazio |
| 31 | A versão mínima do yt-dlp (2024.07.01) não cobria CVEs de 2026, entre eles a escrita de `.desktop` na pasta de destino | alto | `pip-audit` | mínimo subiu para 2026.07.04 |
| 32 | O `Analyzer` validava a URL com uma regra mais fraca que a fila | baixo | própria | as duas usam `is_downloadable_url` |
| 33 | SIGTERM e SIGINT: o `aboutToQuit` fechava o socket de despertar antes da leitura e gerava traceback | baixo | execução real | corrigido |

### Auditoria do motor de downloads

A segunda auditoria, do motor de downloads e da superfície de ataque do yt-dlp e do ffmpeg, está em `docs/threat-model.md`, com as decisões na ADR 0009 e os invariantes em `docs/download-engine.md`.

## Plano executado

Cada etapa foi pequena, com teste antes de seguir. Reverter qualquer uma é restaurar os arquivos listados, sem migração de dados: o formato de `settings.json` e `history.json` não mudou.

| etapa | critério de aceite | verificação |
|---|---|---|
| Camadas | `domain` e `ytdlp` sem Qt; testes sem `QCoreApplication` | `test_architecture.py` |
| Isolamento do yt-dlp | config plantada ignorada pelo yt-dlp real | `test_process_isolation.py` (integração) |
| Validação de entrada | URL, modelo, idiomas, pasta e navegador rejeitam valor inseguro | `test_ytdlp.py`, `test_hardening.py` |
| Máquina de estados | toda transição fora da tabela levanta erro | `test_jobs.py` (tabela inteira) |
| Persistência | gravação atômica fora da thread da interface; falha só registra | `test_storage.py` |
| Instância única e sinais | segunda abertura entrega para a primeira; SIGTERM grava e sai com 0 | `test_instance.py`, `test_signals.py`, execução real no Wayland |
| QML | sem rich text de origem externa; acessibilidade; sem aviso de QML nos 8 cenários | `tools/lint_qml.py`, `test_qml_smoke.py` |
| Gates | um comando local igual ao CI | `scripts/check.sh` |

## Validação

Executado em 18/10/2026 no Fedora 44 (Python 3.14, PySide6 6.11.2 do sistema, yt-dlp 2026.08.19):

- `scripts/check.sh`: ruff sem erros, 53 arquivos formatados, pyright com 0 erros, 170 testes passando, qmllint com 0 problemas, pip-audit sem vulnerabilidades.
- O mesmo script num venv com Python 3.12 e PySide6 6.11.2 do PyPI, como no CI: 170 testes passando, sem aviso de QML.
- `actionlint` no workflow: sem erros.
- Wheel gerado com `uv build`: 44 QML, 39 SVG e `qmldir`. Instalado num venv, o comando `pluck` abriu fora do repositório com dados isolados e gravou o estado no SIGTERM.
- Execução real no KDE Wayland: a segunda instância saiu com código 0 em 0,22 s e a primeira continuou aberta; socket `pluck.sock` com modo 0700 em `/run/user/1000`; SIGTERM gravou `history.json` e `settings.json` no mesmo segundo, saiu com código 0 e removeu o socket; log vazio.
- Testes de mutação manuais: sem o wakeup fd, `test_signals.py` falha; com uma referência quebrada em `StatusBar.qml`, o smoke falha; sem os handlers de teclado, o teste do diálogo falha; sem o lock, o teste de corrida falhou em 2 de 5 rodadas (com o lock, passou em 8 de 8); sem o fim da recursão, o teste da pasta inválida falha.

## Riscos restantes

| risco | por que ficou | recomendação |
|---|---|---|
| O workflow de CI nunca rodou no GitHub | o repositório não tem remoto e publicar exige autorização | publicar e acompanhar o primeiro run; as bibliotecas do Ubuntu para o Qt offscreen são a parte mais provável de precisar de ajuste |
| Config do yt-dlp do usuário e do sistema é confiável | decisão de produto: o usuário espera que ela valha | documentado em `docs/security.md` |
| Arquivos com extensão perigosa ainda podem chegar à pasta com yt-dlp antigo | a correção é do yt-dlp | manter o aviso de versão; considerar bloquear o download abaixo da mínima |
| Acessibilidade não testada com leitor de tela real | só nomes e papéis foram verificados no código | testar com Orca |
| Parse da análise na thread da interface | 4 ms medidos, limitado a 1000 itens | mover para thread se o limite subir |
| Sem LICENSE e sem contato de segurança | escolha do autor | definir licença e um `SECURITY.md` com contato |
| Ícones carregados de forma síncrona, custo do `RoundedCorners`, campo focado fora da área visível nas Configurações | ganho pequeno frente ao risco de mexer agora | revisar se aparecer travada ou problema de navegação por teclado |
| Linux apenas | `notify-send`, `xdg-open`, caminhos XDG | fora do escopo atual |
