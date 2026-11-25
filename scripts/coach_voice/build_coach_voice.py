"""Gera o pacote de áudio do coach de voz do Curva a partir do copy.yaml.

Roda na máquina que tem o VoiceStudio (GPU local). NÃO roda na VPS, não
precisa de Django nem de Postgres.

    python scripts/coach_voice/build_coach_voice.py            # tudo
    python scripts/coach_voice/build_coach_voice.py --limit 5  # amostra
    python scripts/coach_voice/build_coach_voice.py --only set_top
    python scripts/coach_voice/build_coach_voice.py --qa       # + QA por transcrição

Dependências (fora do requirements do app): pyyaml, numpy, scipy, lameenc.

Saídas:
- masters WAV (float 32) em --masters (padrão ~/.octobox/coach_voice_masters),
  fora do repo, cacheados por hash do texto + parâmetros de voz;
- MP3 mono tratado para "furar" a música + manifest.json em
  static/audio/coach/v<version>/.

QA (--qa): o próprio VoiceStudio transcreve cada fala (em lotes de 8, cada
chamada custa ~9 s fixos) e compara com o texto. Lote com palavra faltando é
retranscrito fala a fala; fala reprovada é regerada com outra seed (até 3
vezes) e fica a melhor. As que nem assim passam vão para qa_report.json, a
lista de escuta humana. Número faltando reprova na hora: é a palavra que
mais importa e a que o modelo mais "come" em frase curta.

Tratamento (docs/plans/curva-coach-voz-guiada.md, "mixar a voz"):
corte suave de silêncio → realce 2–4 kHz → corte de graves < 90 Hz →
loudness alto e uniforme → limitador → fade de 40 ms nas pontas.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import unicodedata
import sys
import time
import urllib.request
import uuid
import wave
from collections import Counter
from pathlib import Path

import lameenc
import numpy as np
import yaml
from scipy.signal import butter, lfilter

REPO = Path(__file__).resolve().parents[2]
COPY = REPO / 'public_workouts' / 'coach_voice' / 'copy.yaml'

# ---------------------------------------------------------------- números
_UNI = ['zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove',
        'dez', 'onze', 'doze', 'treze', 'catorze', 'quinze', 'dezesseis', 'dezessete',
        'dezoito', 'dezenove']
_DEZ = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta',
        'oitenta', 'noventa']
_CEN = ['', 'cento', 'duzentos', 'trezentos']


def extenso(n: int, feminino: bool = False) -> str:
    if not 0 <= n < 400:
        raise ValueError(n)
    if n == 100:
        return 'cem'
    partes = []
    c, r = divmod(n, 100)
    if c:
        partes.append(_CEN[c])
    if r or not partes:
        if r < 20:
            partes.append(_UNI[r])
        else:
            d, u = divmod(r, 10)
            partes.append(_DEZ[d] + (f' e {_UNI[u]}' if u else ''))
    texto = ' e '.join(partes)
    if feminino:
        texto = texto.replace('duzentos', 'duzentas').replace('trezentos', 'trezentas')
        for masc, fem in (('um', 'uma'), ('dois', 'duas')):
            if texto == masc or texto.endswith(' ' + masc):
                texto = texto[: -len(masc)] + fem
    return texto


def kg_texto(kg: float) -> str:
    inteiro = int(kg)
    meio = abs(kg - inteiro - 0.5) < 1e-6
    if inteiro == 0:
        return 'meio quilo'
    unidade = 'quilo' if inteiro == 1 else 'quilos'
    return f'{extenso(inteiro)} {unidade}' + (' e meio' if meio else '')


def reps_texto(n: int) -> str:
    return f'{extenso(n, feminino=True)} ' + ('repetição' if n == 1 else 'repetições')


def descanso_texto(seg: int) -> str:
    if seg < 60 or seg % 30:
        return f'{extenso(seg)} segundos'
    minutos, resto = divmod(seg, 60)
    base = 'um minuto' if minutos == 1 else f'{extenso(minutos)} minutos'
    return base + (' e meio' if resto else '')


def kg_id(kg: float) -> str:
    return f'{kg:g}'.replace('.', '_')


# ---------------------------------------------------------------- itens
def expandir(copy: dict, only: set[str] | None) -> list[dict]:
    r = copy['ranges']
    faixas = r['kg'] if isinstance(r['kg'], list) else [r['kg']]
    kgs = set()
    for faixa in faixas:
        if 'values' in faixa:
            kgs.update(float(v) for v in faixa['values'])
        else:
            passos = int(round((faixa['max'] - faixa['min']) / faixa['step']))
            kgs.update(round(faixa['min'] + i * faixa['step'], 2) for i in range(passos + 1))
    kgs = sorted(kgs)
    reps = range(r['reps']['min'], r['reps']['max'] + 1)
    itens = []
    for evento, spec in copy['events'].items():
        if only and evento not in only:
            continue
        if 'variants' in spec:
            for i, texto in enumerate(spec['variants'], 1):
                itens.append({'id': f'{evento}__v{i}', 'event': evento, 'variant': i, 'text': texto})
        elif spec.get('per_load'):
            for kg in kgs:
                itens.append({'id': f'{evento}__kg{kg_id(kg)}', 'event': evento, 'kg': kg,
                              'text': spec['template'].format(kg=kg_texto(kg))})
        elif spec.get('per_value') == 'reps':
            for n in reps:
                itens.append({'id': f'{evento}__r{n}', 'event': evento, 'reps': n,
                              'text': spec['template'].format(reps=reps_texto(n))})
        elif spec.get('per_value') == 'count':
            faixa = spec.get('range', {'min': 1, 'max': 30})
            moldes = spec.get('templates') or [spec['template']]
            for n in range(faixa['min'], faixa['max'] + 1):
                numero = extenso(n)
                for i, molde in enumerate(moldes, 1):
                    sufixo = f'_v{i}' if len(moldes) > 1 else ''
                    itens.append({'id': f'{evento}__r{n}{sufixo}', 'event': evento, 'reps': n, 'variant': i,
                                  'text': molde.format(N=numero[0].upper() + numero[1:], reps=reps_texto(n))})
        elif spec.get('per_value') == 'rest':
            for seg in r['rest']:
                itens.append({'id': f'{evento}__s{seg}', 'event': evento, 'seconds': seg,
                              'text': spec['template'].format(seg=descanso_texto(seg))})
    for item in itens:  # "Descansa. trinta segundos" → "Descansa. Trinta segundos"
        item['text'] = re.sub(r'([.!?]\s+)([a-zà-ú])', lambda m: m.group(1) + m.group(2).upper(), item['text'])
        voz = copy['events'][item['event']].get('voice')
        if voz:  # ex.: speed 0.95 nas falas da reta final da série
            item['voice'] = voz
    return itens


# ---------------------------------------------------------------- QA
QA_LIMIAR = 0.85
QA_LOTE = 8
_NUMEROS = {unicodedata.normalize('NFKD', w).encode('ascii', 'ignore').decode()
            for w in _UNI + _DEZ + _CEN + ['cem', 'meio'] if w}


def _palavras(texto: str) -> list[str]:
    t = texto.lower().replace('kg', ' quilos ')
    t = re.sub(r'\btop\s*(7|sete|sets?)\b', 'top set', t)
    t = re.sub(r'(\d+)[,.]5\b', r'\1 e meio', t)
    t = re.sub(r'\d+', lambda m: f' {extenso(int(m.group()))} ' if int(m.group()) < 400 else m.group(), t)
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return [{'uma': 'um', 'duas': 'dois', 'para': 'pra'}.get(w, w) for w in re.findall(r'[a-z]+', t) if w != 'e']


def faltando(texto: str, ouvido: str) -> Counter:
    """Palavras do texto que a transcrição não ouviu (multiconjunto: repetida conta duas vezes)."""
    return Counter(_palavras(texto)) - Counter(_palavras(ouvido))


def nota_qa(texto: str, ouvido: str) -> float:
    """Fração das palavras do texto que a transcrição ouviu; número faltando = 0."""
    esperado = Counter(_palavras(texto))
    faltam = faltando(texto, ouvido)
    if any(w in _NUMEROS for w in faltam):
        return 0.0
    return 1 - sum(faltam.values()) / max(sum(esperado.values()), 1)


def wav16(x: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    return buf.getvalue()


def transcrever(x: np.ndarray, sr: int, base_url: str) -> str | None:
    # 0,5 s de silêncio antes: sem isso o transcritor engole a 1ª palavra
    dados = wav16(np.concatenate([np.zeros(int(sr * 0.5)), x]), sr)
    limite = uuid.uuid4().hex
    cabecalho = (f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="qa.wav"\r\nContent-Type: audio/wav\r\n\r\n')
    rodape = (f'\r\n--{limite}\r\nContent-Disposition: form-data; name="language"\r\n\r\npt\r\n--{limite}--\r\n')
    corpo = cabecalho.encode() + dados + rodape.encode()
    req = urllib.request.Request(f'{base_url}/v1/audio/transcriptions', data=corpo, method='POST',
                                 headers={'Content-Type': f'multipart/form-data; boundary={limite}'})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode('utf-8')).get('text', '').strip()
    except Exception as exc:  # QA é rede de proteção: sem transcrição, a fala segue sem nota
        print(f'  transcrição falhou: {exc!r}', flush=True)
        return None


# ---------------------------------------------------------------- VoiceStudio
def gerar(voice: dict, texto: str, base_url: str, seed: int | None = None) -> bytes:
    campos = {'text': texto, 'language': voice['language'], 'profile_id': voice['profile_id'],
              'num_step': str(voice['steps']), 'speed': str(voice['speed']), 'wav_bits': '32'}
    if seed is not None:
        campos['seed'] = str(seed)
    limite = uuid.uuid4().hex
    corpo = b''.join(
        f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, v in campos.items()) + f'--{limite}--\r\n'.encode()
    req = urllib.request.Request(f'{base_url}/generate', data=corpo, method='POST',
                                 headers={'Content-Type': f'multipart/form-data; boundary={limite}'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def gerar_com_retentativa(voice: dict, texto: str, base_url: str, tentativas: int = 3):
    for tentativa in range(1, tentativas + 1):
        try:
            # retentativa troca a seed: a mesma seed repetiria a mesma falha
            seed = voice.get('seed')
            seed = None if seed is None else seed + tentativa - 1
            x, sr = ler_wav(gerar(voice, texto, base_url, seed))
            if len(x) >= sr * 0.5:  # menos de meio segundo = geração quebrada
                return x, sr
            erro = f'áudio curto demais ({len(x) / sr:.2f}s)'
        except Exception as exc:  # VoiceStudio reiniciando, GPU ocupada, timeout
            erro = repr(exc)
        print(f'  tentativa {tentativa}/{tentativas} falhou: {erro}', flush=True)
        time.sleep(5 * tentativa)
    raise RuntimeError(f'VoiceStudio não gerou: {texto!r}')


def sr_minimo(x) -> int:
    """Tamanho mínimo aceitável de um master do cache (amostras)."""
    return 0 if x is None else 8000


def ler_wav(dados: bytes) -> tuple[np.ndarray, int]:
    """Lê PCM 16/24/32 bits ou float 32 (wave não lê float, então parse manual)."""
    fmt = dados.find(b'fmt ')
    tag, canais, sr = struct.unpack('<HHI', dados[fmt + 8:fmt + 16])
    bits = struct.unpack('<H', dados[fmt + 22:fmt + 24])[0]
    if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE: subformato nos 2 primeiros bytes do GUID
        tag = struct.unpack('<H', dados[fmt + 32:fmt + 34])[0]
    pos = dados.find(b'data')
    tam = struct.unpack('<I', dados[pos + 4:pos + 8])[0]
    bruto = dados[pos + 8:pos + 8 + tam]
    if tag == 3:
        x = np.frombuffer(bruto, '<f4').astype(np.float64)
    elif bits == 16:
        x = np.frombuffer(bruto, '<i2') / 32768.0
    elif bits == 24:
        b = np.frombuffer(bruto, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(v >= 1 << 23, v - (1 << 24), v) / float(1 << 23)
    else:
        x = np.frombuffer(bruto, '<i4') / 2147483648.0
    return x.reshape(-1, canais).mean(axis=1), sr


# ---------------------------------------------------------------- tratamento
def _peaking(f0, gain_db, q, sr):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / sr
    alpha = np.sin(w) / (2 * q)
    b = [1 + alpha * a, -2 * np.cos(w), 1 - alpha * a]
    den = [1 + alpha / a, -2 * np.cos(w), 1 - alpha / a]
    return np.array(b) / den[0], np.array(den) / den[0]


def remover_estalo(x: np.ndarray, sr: int) -> np.ndarray:
    """Corta o "dá" que o modelo solta antes da fala.

    Em 473 de 488 masters (varredura de 2026-11-16) a saída começa com um
    estalo de ~100 ms em ~50 ms, depois ~300 ms de silêncio, e só então a fala.
    Corta do começo até o fim desse silêncio. Sem esse desenho (som começando
    depois de 150 ms, ou sem silêncio de 60 ms antes de 450 ms) não mexe.
    """
    w = max(int(sr * 0.01), 1)
    n = len(x) // w
    if n < 50:
        return x
    db = 20 * np.log10(np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-9)
    som = int(np.argmax(db > -35))
    if not db[som] > -35 or som > 15:
        return x
    i = som
    while i < 45:
        if db[i] < -45:
            j = i
            while j < n and db[j] < -45:
                j += 1
            if j - i >= 6:
                return x[max(j * w - int(sr * 0.03), 0):]
            i = j
        else:
            i += 1
    return x


def tratar(x: np.ndarray, sr: int, alvo_rms_db: float = -16.0) -> np.ndarray:
    x = remover_estalo(x, sr)
    # corte suave de silêncio (−60 dB, 150 ms de folga: não come consoante)
    janela = max(int(sr * 0.01), 1)
    env = np.sqrt(np.convolve(x ** 2, np.ones(janela) / janela, 'same') + 1e-12)
    voz = np.where(20 * np.log10(env) > -60)[0]
    if len(voz):
        folga = int(sr * 0.15)
        x = x[max(voz[0] - folga, 0):voz[-1] + folga]
    # graves fora (< 90 Hz): só embolam com o bumbo da música
    b, a = butter(2, 90 / (sr / 2), 'highpass')
    x = lfilter(b, a, x)
    # presença: +4 dB em 3 kHz, onde a fala se separa da música
    b, a = _peaking(3000, 4.0, 0.9, sr)
    x = lfilter(b, a, x)
    # loudness alto e uniforme
    rms = np.sqrt(np.mean(x ** 2)) + 1e-12
    x = x * 10 ** ((alvo_rms_db - 20 * np.log10(rms)) / 20)
    # limitador suave: picos acima de −3 dBFS arredondados, teto −1 dBFS
    teto, joelho = 10 ** (-1 / 20), 10 ** (-3 / 20)
    acima = np.abs(x) > joelho
    x[acima] = np.sign(x[acima]) * (joelho + (teto - joelho) * np.tanh((np.abs(x[acima]) - joelho) / (teto - joelho)))
    # fade de 40 ms nas pontas (sem clique)
    n = int(sr * 0.04)
    rampa = np.linspace(0, 1, n)
    x[:n] *= rampa
    x[-n:] *= rampa[::-1]
    return x


def bip(sr: int) -> np.ndarray:
    """Dois tons curtos subindo (880 → 1320 Hz), ~200 ms, para chamar atenção."""
    def tom(f, dur):
        t = np.arange(int(sr * dur)) / sr
        env = np.minimum(1, np.minimum(t / 0.008, (dur - t) / 0.03))
        return 0.5 * np.sin(2 * np.pi * f * t) * env
    return np.concatenate([tom(880, 0.08), np.zeros(int(sr * 0.03)), tom(1320, 0.09)])


def toque(sr: int, frequencia: float, dur: float) -> np.ndarray:
    """Bip da contagem regressiva da série (o mesmo 660 / 990 Hz do 3-2-1 do app)."""
    t = np.arange(int(sr * dur)) / sr
    return 0.5 * np.sin(2 * np.pi * frequencia * t) * np.minimum(1, t / 0.005) * np.exp(-t * 9)


def mp3(x: np.ndarray, sr: int, kbps: int) -> bytes:
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    return enc.encode(pcm) + enc.flush()


def wav_f32(x: np.ndarray, sr: int) -> bytes:
    d = x.astype('<f4').tobytes()
    return (b'RIFF' + struct.pack('<I', 36 + len(d)) + b'WAVEfmt '
            + struct.pack('<IHHIIHH', 16, 3, 1, sr, sr * 4, 4, 32) + b'data' + struct.pack('<I', len(d)) + d)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--copy', type=Path, default=COPY)
    ap.add_argument('--masters', type=Path, default=Path.home() / '.octobox' / 'coach_voice_masters')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--voicestudio', default='http://127.0.0.1:3900')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--kbps', type=int, default=96)
    ap.add_argument('--qa', action='store_true', help='transcreve e regera falas com palavra faltando')
    args = ap.parse_args()

    if sys.platform == 'win32':
        # Pede ao Windows para não dormir só enquanto ESTE processo roda (como um
        # player de vídeo faz). Não muda configuração de energia; some ao sair.
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    copy = yaml.safe_load(args.copy.read_text(encoding='utf-8'))
    voice = copy['voice']
    out = args.out or REPO / 'static' / 'audio' / 'coach' / f"v{copy['version']}"
    out.mkdir(parents=True, exist_ok=True)
    args.masters.mkdir(parents=True, exist_ok=True)

    itens = expandir(copy, set(args.only) if args.only else None)
    if args.limit:
        itens = itens[: args.limit]
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    clips = manifest.get('clips', {})

    def salvar_manifesto():
        dados = {'version': copy['version'], 'voice': voice, 'beep': 'bip.mp3', 'tick': 'tick.mp3',
                 'go': 'go.mp3', 'clips': clips}
        tmp = manifest_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding='utf-8')
        tmp.replace(manifest_path)

    def assinatura_de(voz: dict) -> str:
        return json.dumps({k: voz.get(k) for k in ('profile_id', 'language', 'speed', 'steps', 'seed')},
                          sort_keys=True)

    def gravar_master(master: Path, x: np.ndarray, sr: int) -> None:
        tmp = master.with_suffix('.tmp')  # grava atômico: um kill não deixa master pela metade
        tmp.write_bytes(wav_f32(x, sr))
        tmp.replace(master)

    sr_saida = None
    inicio = time.time()
    para_qa = []
    for n, item in enumerate(itens, 1):
        voz = {**voice, **item.get('voice', {})}
        chave = hashlib.sha256((assinatura_de(voz) + item['text']).encode()).hexdigest()[:16]
        master = args.masters / f'{chave}.wav'
        destino = out / f"{item['id']}.mp3"
        x = None
        if master.exists():
            try:
                x, sr = ler_wav(master.read_bytes())
                origem = 'cache'
            except Exception:  # master truncado por uma interrupção antiga: refaz
                x = None
        if x is None or len(x) < sr_minimo(x):
            x, sr = gerar_com_retentativa(voz, item['text'], args.voicestudio)
            gravar_master(master, x, sr)
            origem = 'gerado'
        sr_saida = sr
        y = None
        if clips.get(item['id'], {}).get('hash') != chave or not destino.exists():
            y = tratar(x, sr)
            destino.write_bytes(mp3(y, sr, args.kbps))
            clips[item['id']] = {**{k: v for k, v in item.items() if k not in ('id', 'voice')},
                                 'file': destino.name, 'hash': chave,
                                 'duration_s': round(len(y) / sr, 2)}
            if 'voice' in item:
                clips[item['id']]['speed'] = voz['speed']
        if args.qa and 'qa' not in clips[item['id']]:
            para_qa.append({'id': item['id'], 'text': item['text'], 'voz': voz, 'master': master,
                            'destino': destino, 'sr': sr, 'y': (tratar(x, sr) if y is None else y).astype(np.float32)})
        decorrido = time.time() - inicio
        print(f'[{n}/{len(itens)}] {origem:6} {item["id"]:28} {decorrido:6.0f}s  {item["text"]}', flush=True)
        if n % 10 == 0:  # retomável: uma interrupção perde no máximo 10 entradas do manifesto
            salvar_manifesto()
    salvar_manifesto()

    # ---- QA: lote de 8 numa chamada; lote com palavra faltando → fala a fala
    # Ordem embaralhada (semente fixa): 8 frases quase iguais seguidas ("A carga
    # dessa série é…") o transcritor junta numa só e o lote inteiro reprova.
    para_qa.sort(key=lambda e: hashlib.sha1(e['id'].encode()).hexdigest())
    for i in range(0, len(para_qa), QA_LOTE):
        lote = para_qa[i:i + QA_LOTE]
        sr = lote[0]['sr']
        pausa = np.zeros(int(sr * 1.2), np.float32)
        ouvido = transcrever(np.concatenate([s for e in lote for s in (e['y'], pausa)]), sr, args.voicestudio)
        if ouvido is None:
            continue  # VoiceStudio sem transcrição: fica para a próxima rodada
        faltam = faltando(' '.join(e['text'] for e in lote), ouvido)
        if sum(faltam.values()) <= 1 and not any(w in _NUMEROS for w in faltam):
            for e in lote:
                clips[e['id']]['qa'] = 1.0
            print(f'QA lote {i // QA_LOTE + 1}: ok', flush=True)
            salvar_manifesto()
            continue
        print(f'QA lote {i // QA_LOTE + 1}: faltou {dict(faltam)} → fala a fala', flush=True)
        for e in lote:
            ouvido = transcrever(e['y'], sr, args.voicestudio)
            if ouvido is None:
                continue
            melhor = (nota_qa(e['text'], ouvido), e['y'], ouvido, None, None)
            tentativa = 0
            caiu = False
            while melhor[0] < QA_LIMIAR and tentativa < 3:
                tentativa += 1
                voz = {**e['voz'], 'seed': (e['voz'].get('seed') or 0) + 100 * tentativa}
                try:
                    x2, sr2 = gerar_com_retentativa(voz, e['text'], args.voicestudio)
                except RuntimeError as exc:
                    print(f'  {e["id"]}: {exc} — fica para a próxima rodada', flush=True)
                    caiu = True
                    break
                y2 = tratar(x2, sr2).astype(np.float32)
                o2 = transcrever(y2, sr2, args.voicestudio) or ''
                if nota_qa(e['text'], o2) > melhor[0]:
                    melhor = (nota_qa(e['text'], o2), y2, o2, voz['seed'], x2)
            if caiu and melhor[3] is None:
                continue
            nota, y, ouvido, seed, x = melhor
            if x is not None:  # outra seed passou melhor: vira o master e o MP3
                gravar_master(e['master'], x, sr)
                e['destino'].write_bytes(mp3(y, sr, args.kbps))
                clips[e['id']].update(duration_s=round(len(y) / sr, 2), seed=seed)
            clips[e['id']]['qa'] = round(nota, 2)
            if nota < QA_LIMIAR:
                clips[e['id']]['qa_ouvido'] = ouvido  # o relatório de escuta sai daqui
            print(f'  {e["id"]:28} nota {nota:.2f}  {e["text"]!r} → {ouvido!r}', flush=True)
        salvar_manifesto()
    if args.qa:
        textos = {item['id']: item['text'] for item in itens}
        relatorio = [{'id': k, 'texto': textos.get(k), 'ouvido': c.get('qa_ouvido'), 'nota': c['qa']}
                     for k, c in clips.items() if c.get('qa', 1) < QA_LIMIAR]
        sem_nota = [k for k, c in clips.items() if 'qa' not in c]
        destino_rel = args.masters / f"qa_report_v{copy['version']}.json"
        destino_rel.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'QA: {len(para_qa)} checadas nesta rodada, {len(relatorio)} para escuta humana, '
              f'{len(sem_nota)} sem nota (rodar de novo) → {destino_rel}')

    if sr_saida:
        (out / 'bip.mp3').write_bytes(mp3(bip(sr_saida), sr_saida, args.kbps))
        (out / 'tick.mp3').write_bytes(mp3(toque(sr_saida, 660, 0.12), sr_saida, args.kbps))
        (out / 'go.mp3').write_bytes(mp3(toque(sr_saida, 990, 0.24), sr_saida, args.kbps))
    salvar_manifesto()
    total = sum(p.stat().st_size for p in out.glob('*.mp3'))
    print(f'ok: {len(clips)} falas no manifesto, {total / 1e6:.1f} MB em {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
