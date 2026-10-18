from __future__ import annotations

import re
from collections import deque

from pluck.application.ports import Failure

STDERR_TAIL_LINES = 30


LAUNCH_FAILURE = "Não foi possível iniciar o yt-dlp. Instale com: sudo dnf install yt-dlp"


CRASH_MESSAGE = "O yt-dlp foi encerrado inesperadamente."

ERROR_HINTS = (
    ("confirm your age", "Vídeo com restrição de idade. Ative os cookies do navegador em Configurações."),
    ("not a bot", "O YouTube pediu login pra liberar o vídeo. Ative os cookies do navegador em Configurações."),
    ("Private video", "Vídeo privado."),
    ("members-only", "Vídeo exclusivo pra membros do canal."),
    ("This live event will begin", "A transmissão ainda não começou."),
    ("Video unavailable", "Vídeo indisponível."),
    ("This video is not available", "Vídeo indisponível."),
    ("Unsupported URL", "Esse link não é suportado."),
    ("is not a valid URL", "Isso não parece um link válido."),
    ("Requested format is not available", "Esse formato não está disponível pra esse vídeo."),
    ("HTTP Error 429", "O site limitou as requisições. Espere alguns minutos e tente de novo."),
    ("HTTP Error 403", "O site recusou o acesso (HTTP 403)."),
    ("HTTP Error 404", "Conteúdo não encontrado (HTTP 404)."),
    ("Temporary failure in name resolution", "Sem conexão com a internet."),
    ("getaddrinfo failed", "Sem conexão com a internet."),
    ("Name or service not known", "Sem conexão com a internet."),
    ("Unable to download webpage", "Não foi possível acessar o site. Verifique a conexão."),
    ("No space left on device", "Sem espaço em disco."),
    ("Permission denied", "Sem permissão pra gravar na pasta de destino."),
    ("ffmpeg not found", "ffmpeg não encontrado. Instale com: sudo dnf install ffmpeg"),
    ("cookies database", "Não foi possível ler os cookies do navegador escolhido."),
)


PERMANENT_ERRORS = re.compile(
    r"private video|members-only|confirm your age|not a bot|unavailable|not available|unsupported url|"
    r"not a valid url|live event will begin|http error (?:40[0-9]|41[0-9])|no space left|permission denied|"
    r"ffmpeg not found|cookies database|unsafe file extension",
    re.IGNORECASE,
)


RATE_LIMITED_ERRORS = re.compile(r"http error 429|too many requests", re.IGNORECASE)


SERVER_ERRORS = re.compile(r"http error 5\d\d", re.IGNORECASE)


TRANSIENT_ERRORS = re.compile(
    r"timed out|temporary failure in name resolution|name or service not known|getaddrinfo failed|"
    r"network is unreachable|connection (?:reset|refused|aborted)|remote end closed connection|incompleteread|"
    r"eof occurred in violation of protocol",
    re.IGNORECASE,
)


def is_rate_limited(headline: str) -> bool:
    return bool(RATE_LIMITED_ERRORS.search(headline))


def is_transient(headline: str) -> bool:
    if is_rate_limited(headline) or SERVER_ERRORS.search(headline):
        return True
    return not PERMANENT_ERRORS.search(headline) and bool(TRANSIENT_ERRORS.search(headline))


def error_detail(raw: str) -> str:
    return redact(re.sub(r"^ERROR:\s*", "", raw.strip()))


def friendly_error(raw: str) -> str:
    for needle, message in ERROR_HINTS:
        if needle.lower() in raw.lower():
            return message
    detail = error_detail(raw)
    detail = re.sub(r"^\[[^\]]+\]\s*", "", detail)
    return detail or "O yt-dlp encerrou com erro."


SENSITIVE_QUERY_VALUE = re.compile(
    r"([?&](?:ip|sig|signature|lsig|key|token|access_token|auth|authorization|cookie|session|sid|password|pass|pot)=)"
    r"[^&\s'\"]*",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    return SENSITIVE_QUERY_VALUE.sub(r"\1[redacted]", text)


class StderrTail:
    def __init__(self, limit: int = STDERR_TAIL_LINES):
        self._lines: deque[str] = deque(maxlen=limit)
        self._errors: deque[str] = deque(maxlen=limit)

    def add(self, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return
        self._lines.append(line)
        if line.startswith("ERROR:"):
            self._errors.append(line)

    @property
    def text(self) -> str:
        return "\n".join(self._lines)

    @property
    def headline(self) -> str:
        if self._errors:
            return self._errors[-1]
        return self._lines[-1] if self._lines else ""


def exit_message(headline: str, exit_code: int) -> str:
    return friendly_error(headline) if headline else f"O yt-dlp encerrou com código {exit_code}."


def download_failure(tail: StderrTail, exit_code: int, crashed: bool = False) -> Failure:
    detail = redact(tail.text) or error_detail(tail.headline)
    if crashed:
        return Failure(CRASH_MESSAGE, detail)
    headline = tail.headline
    return Failure(
        exit_message(headline, exit_code),
        detail,
        transient=is_transient(headline),
        rate_limited=is_rate_limited(headline),
    )


def analysis_failure(output: str, exit_code: int) -> Failure:
    tail = StderrTail()
    for line in output.splitlines():
        tail.add(line)
    return Failure(exit_message(tail.headline, exit_code), error_detail(tail.text))


def launch_failure(executable: str, reason: str) -> Failure:
    return Failure(LAUNCH_FAILURE, f"{executable}: {reason}")
