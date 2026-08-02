"""Estruturas de dados da pipeline de transcricao.

Tudo aqui e' puro (sem I/O, sem modelo de ML) para permitir teste unitario
das regras de negocio, que e' onde mora o risco real do projeto.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    """Destino de um segmento apos as regras de qualidade."""

    OK = "ok"                    # confianca alta, pode ir para a fila de publicacao
    REVISAR = "revisar"          # exige conferencia humana antes de qualquer uso
    DESCARTADO = "descartado"    # provavel silencio/musica/alucinacao, nao usar


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str
    probabilidade: float
    falante: Optional[str] = None

    @property
    def duracao(self) -> float:
        return max(0.0, self.fim - self.inicio)


@dataclass
class Turno:
    """Intervalo de fala de um falante, vindo da diarizacao."""

    inicio: float
    fim: float
    falante: str

    @property
    def duracao(self) -> float:
        return max(0.0, self.fim - self.inicio)


@dataclass
class Segmento:
    """Segmento transcrito, com as metricas de confianca do Whisper."""

    inicio: float
    fim: float
    texto: str
    avg_logprob: float
    no_speech_prob: float
    compression_ratio: float
    palavras: list[Palavra] = field(default_factory=list)
    falante: Optional[str] = None
    pureza_falante: float = 1.0
    status: Status = Status.OK
    motivos: list[str] = field(default_factory=list)

    @property
    def duracao(self) -> float:
        return max(0.0, self.fim - self.inicio)

    @property
    def citavel(self) -> bool:
        """Nunca publique direto: citavel significa 'pode entrar na fila humana'."""
        return self.status is Status.OK


@dataclass
class Transcricao:
    """Resultado completo de um item de midia."""

    proveniencia: dict[str, Any]
    idioma: str
    duracao: float
    segmentos: list[Segmento] = field(default_factory=list)
    falantes: list[str] = field(default_factory=list)
    diarizacao_disponivel: bool = False
    avisos: list[str] = field(default_factory=list)

    @property
    def multi_falante(self) -> bool:
        return len(self.falantes) > 1

    @property
    def exige_revisao_humana(self) -> bool:
        """Regra de produto travada no codigo.

        Conteudo com mais de um falante, ou sem diarizacao confiavel, so vai
        ao ar depois de conferencia humana da atribuicao. Atribuir fala de
        entrevistador a candidato e' o erro que destroi o projeto.
        """
        if self.multi_falante:
            return True
        if not self.diarizacao_disponivel:
            return True
        return any(s.status is Status.REVISAR for s in self.segmentos)

    def para_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["exige_revisao_humana"] = self.exige_revisao_humana
        d["multi_falante"] = self.multi_falante
        for seg in d["segmentos"]:
            seg["status"] = (
                seg["status"].value
                if isinstance(seg["status"], Status)
                else str(seg["status"])
            )
        return d
