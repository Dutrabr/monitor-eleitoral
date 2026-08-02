# Monitor Eleitoral — modulo de transcricao

Transcricao de audio/video com **cadeia de custodia**, **diarizacao** (quem
falou) e **descarte por confianca** (anti-alucinacao).

Projetado para uso jornalistico: a transcricao encontra a fala em escala, um
humano confere antes de qualquer publicacao.

## Instalacao (macOS, Apple Silicon)

Nao coloque o projeto nem a venv dentro de pasta sincronizada por iCloud —
sincronizacao corrompe venv.

```bash
mkdir -p ~/Projetos/monitor-eleitoral && cd ~/Projetos/monitor-eleitoral
# copie os arquivos deste pacote aqui

git init && git add -A && git commit -m "modulo de transcricao"

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg
```

## Rodar sem baixar modelo

```bash
python3 -m pytest tests/ -q   # 41 testes
python3 demo.py               # pipeline completa com transcritor falso
```

O `demo.py` mostra os dois cenarios que importam: entrevista com dois falantes
(vai para revisao obrigatoria) e alucinacao do Whisper em silencio (descartada
por cinco sinais independentes).

## Uso real

```bash
export HF_TOKEN=...   # sem isso, diarizacao desliga e tudo vai para revisao

cd src
python3 -m transcricao.cli ~/midia/live_candidato.mp4 \
    --fonte youtube \
    --url "https://www.youtube.com/watch?v=..." \
    --perfil "@canaloficial" \
    --coletado-em "2026-07-29T21:00:00+00:00" \
    --max-falantes 4 \
    --saida ~/dados/transcricoes
```

Para lote, aponte para uma pasta: o modelo carrega uma vez.

## Saida

Por item, dois arquivos:

- `NOME.transcricao.json` — proveniencia completa, todos os segmentos com
  metricas de confianca, palavras com timestamp e falante.
- `NOME.fila_revisao.json` — apenas o que nao foi descartado, com `timestamp`
  em `HH:MM:SS` para o revisor pular direto ao trecho no video original.

## Status dos segmentos

| Status | Significado |
|---|---|
| `ok` | confianca alta; pode entrar na fila de conferencia |
| `revisar` | algum sinal duvidoso; conferencia obrigatoria |
| `descartado` | silencio, musica ou alucinacao; nao usar |

`ok` **nao** significa "publicavel". Significa "pode ir para o humano".

## Sinais usados no descarte

- `no_speech_prob` alto (trecho sem fala)
- `avg_logprob` baixo (modelo pouco confiante)
- `compression_ratio` alto (texto repetitivo, loop)
- fracao de palavras com `probability` baixa
- taxa implausivel de caracteres por segundo
- frases de alucinacao conhecidas em pt-BR ("Legendas pela comunidade...")
- repeticao interna e repeticao entre segmentos consecutivos
- pureza de falante abaixo do limiar (segmento mistura vozes)

Ajuste os limiares em `src/transcricao/qualidade.py` contra amostra rotulada a
mao, e publique a taxa de erro medida.

## Sobre a diarizacao

`pyannote` diz que existem N falantes diferentes, nao quem sao. O mapeamento de
`SPEAKER_00` para um nome real vem de conferencia humana:

```bash
echo '{"SPEAKER_00": "candidato_x"}' > mapa.json
python3 -m transcricao.cli video.mp4 --mapa-falantes mapa.json --fonte debate
```

Nunca deduza esse mapeamento automaticamente sem validacao.
