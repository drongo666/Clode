"""Build voices, SFX, music, final mix and timeline.json for episode 1.

Usage: python3 build_audio.py   (run from cartoon/ep01)
Needs: piper-tts, ffmpeg, voices in ../voices/
"""
import json, os, subprocess, wave
import numpy as np

SR = 44100
FPS = 24
HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = os.path.join(HERE, '..', 'voices')
OUT = os.path.join(HERE, 'build')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

# speaker -> (piper model, length_scale, pitch ratio, tempo)
VOICE = {
    'K': ('ru_RU-ruslan-medium', 1.08, 0.80, 1.0),   # Дед Кардан: низкий, медленный
    'H': ('ru_RU-dmitri-medium', 0.95, 1.10, 1.04),  # Хрустам: мультяшный, бодрый
}

# Sequence: ('line', spk, text, cam, extras) | ('pause', sec, cam, extras)
SEQ = [
    ('pause', 1.4, 'wide', {'enter': True, 'sfx': 'steps'}),
    ('line', 'H', 'Дед Карда́н! Я решил! Покупаю байк!', 'wide', {}),
    ('line', 'K', 'О-о-о. Ещё один первосезо́нник. Ну, садись. Какой хочешь?', 'K', {}),
    ('line', 'H', 'Спортбайк! Литр! Сотня за три секунды!', 'wide', {'dream': True}),
    ('pause', 1.0, 'wide', {'spit': True, 'sfx': 'spit'}),
    ('line', 'K', 'Литр?! Сынок, ты на велосипеде без рук ездить умеешь?', 'K', {}),
    ('line', 'H', 'Ну... один раз пробовал. В кусты.', 'H', {'shy': True}),
    ('line', 'K', 'Вот. Литр — это те же кусты. Только на двухстах. И кусты из бетона.', 'K', {}),
    ('pause', 2.8, 'gag', {'sfx': 'gag'}),
    ('line', 'H', 'Но он же красивый! Обвес, выхлоп, колено по асфальту!', 'wide', {'dream': True}),
    ('line', 'K', 'Колено по асфальту у тебя будет. В первый же день. Вместе со всем остальным.', 'K', {}),
    ('line', 'H', 'Ладно. Тогда шестьсот кубов?', 'H', {}),
    ('line', 'K', 'Шестисотый спорт крутится до пятнадцати тысяч оборотов. Ты сначала до пятнадцати считать научись. Не сбиваясь.', 'K', {}),
    ('pause', 1.6, 'H', {'count': True}),
    ('line', 'H', 'Да что тогда?! Мопед, что ли?', 'H', {}),
    ('line', 'K', 'Не мопед. Нормальный дорожник. Кубов четыреста — шестьсот. Посадка прямая, падать не жалко, запчасти копеечные. Он тебя всему научит.', 'wide', {'reveal': 4.5}),
    ('line', 'H', 'А спорт когда?', 'H', {}),
    ('line', 'K', 'Сезона через два. Запомни: байкеры бывают двух типов. Которые уже падали. И которые ещё упадут.', 'K', {}),
    ('line', 'H', 'А ты, дед, какой?', 'H', {}),
    ('line', 'K', 'Я третий. Я падал столько, что асфальт меня сам объезжает. Кхе-кхе-кхе!', 'K', {'laugh': True}),
    ('line', 'H', 'Ладно... Беру дорожник. Но покрашу как спорт!', 'wide', {}),
    ('line', 'K', 'Вот это по-нашему!', 'wide', {'thumb': True}),
    ('pause', 3.6, 'title', {'sfx': 'rev'}),
]
GAP = 0.3


# ---------- helpers ----------
def read_wav(p):
    w = wave.open(p)
    sr, n = w.getframerate(), w.getnframes()
    x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    if w.getnchannels() == 2:
        x = x.reshape(-1, 2).mean(1)
    if sr != SR:
        t = np.arange(int(len(x) * SR / sr)) * sr / SR
        x = np.interp(t, np.arange(len(x)), x).astype(np.float32)
    return x


def write_wav(p, x):
    x = np.clip(x, -1, 1)
    w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype(np.int16).tobytes()); w.close()


def fft_filter(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x)).astype(np.float32)


def smooth(x, n):
    return np.convolve(x, np.ones(n) / n, 'same')


def env(n, a, d):
    e = np.ones(n, np.float32)
    ai, di = int(a * SR), int(d * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if di: e[-di:] *= np.linspace(1, 0, di)
    return e


def tts(spk, text, idx):
    model, ls, pitch, tempo = VOICE[spk]
    raw = os.path.join(OUT, f'raw_{idx:02d}.wav')
    proc = os.path.join(OUT, f'line_{idx:02d}.wav')
    subprocess.run(['python3', '-m', 'piper', '-m', os.path.join(VOICES, model + '.onnx'),
                    '-f', raw, '--length-scale', str(ls)], input=text.replace('́', '').encode(),
                   check=True, capture_output=True)
    at = tempo / pitch
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af',
                    f'asetrate={int(22050 * pitch)},aresample=44100,atempo={at:.4f}',
                    '-ar', str(SR), '-ac', '1', proc], check=True)
    x = read_wav(proc)
    if spk == 'K':  # хрипотца: мягкий перегруз + шум по огибающей
        e = smooth(np.abs(x), 600)
        x = np.tanh(x * 3.0) / np.tanh(3.0) * 0.7
        rasp = fft_filter(rng.standard_normal(len(x)).astype(np.float32), 900, 4500)
        x = x + rasp * e * 0.9
        x = x + fft_filter(x, 60, 220) * 0.6  # бас
    else:
        x = x + fft_filter(x, 90, 250) * 0.3
    x = x / (np.abs(x).max() + 1e-6) * 0.9
    return x


def lip_env(x):
    hop = SR // FPS
    v = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    v = v / (np.percentile(v, 95) + 1e-6)
    return [round(float(min(1, max(0, (a - 0.12) * 1.3))), 2) for a in v]


# ---------- SFX ----------
def sfx_steps():
    out = np.zeros(int(1.3 * SR), np.float32)
    for k in range(6):
        i = int((0.1 + k * 0.19) * SR); n = int(0.08 * SR)
        t = np.arange(n) / SR
        out[i:i + n] += (np.sin(2 * np.pi * 90 * t) * np.exp(-t * 50) * 0.5
                         + fft_filter(rng.standard_normal(n).astype(np.float32), 200, 2000) * np.exp(-t * 80) * 0.3)
    return out


def sfx_spit():
    n = int(0.6 * SR); t = np.arange(n) / SR
    noise = fft_filter(rng.standard_normal(n).astype(np.float32), 800, 7000)
    return noise * np.exp(-t * 6) * (t > 0.05) * 0.5


def sfx_whoosh(d=0.9):
    n = int(d * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32); seg = 2048
    for i in range(0, n, seg):
        c = 300 + 3000 * (i / n)
        out[i:i + seg] = fft_filter(noise[i:i + seg], c * 0.5, c * 1.5)[:len(out[i:i + seg])]
    return out * np.sin(np.pi * t / d) ** 2 * 0.8


def sfx_engine(d, f0, f1, vol=0.5):
    n = int(d * SR); t = np.arange(n) / SR
    f = np.linspace(f0, f1, n) ** 1.0
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sign(np.sin(ph)) * 0.4 + np.sin(ph * 2) * 0.3 + np.sin(ph * 0.5) * 0.4)
    x *= 0.6 + 0.4 * np.sin(ph * 0.5) ** 2
    x = np.tanh(x * 2) + fft_filter(rng.standard_normal(n).astype(np.float32), 100, 1500) * 0.2
    return fft_filter(x.astype(np.float32), 30, 2500) * env(n, 0.1, 0.4) * vol


def sfx_crash():
    n = int(1.2 * SR); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (60 - 30 * t) * t) * np.exp(-t * 5)
    noise = rng.standard_normal(n).astype(np.float32) * np.exp(-t * 4)
    leaves = fft_filter(rng.standard_normal(n).astype(np.float32), 2000, 8000) * np.exp(-t * 2.5) * 0.4
    clank = sum(np.sin(2 * np.pi * fr * t) * np.exp(-t * 9) for fr in (523, 787, 1210)) * 0.15
    return (boom * 0.9 + noise * 0.4 + leaves + clank).astype(np.float32)


def sfx_gag():
    out = np.zeros(int(2.8 * SR), np.float32)
    e = sfx_engine(1.2, 90, 260, 0.45); out[:len(e)] += e
    w = sfx_whoosh(0.8); i = int(0.7 * SR); out[i:i + len(w)] += w
    c = sfx_crash(); i = int(1.35 * SR); out[i:i + len(c)] += c
    return out


def sfx_rev():
    out = np.zeros(int(3.6 * SR), np.float32)
    a = sfx_engine(0.8, 45, 140, 0.5); out[:len(a)] += a
    b = sfx_engine(1.6, 50, 220, 0.6); i = int(0.9 * SR); out[i:i + len(b)] += b
    return out


SFX = {'steps': sfx_steps, 'spit': sfx_spit, 'gag': sfx_gag, 'rev': sfx_rev}


# ---------- music ----------
def music(total):
    bpm = 112; beat = 60 / bpm
    n = int(total * SR); out = np.zeros(n, np.float32)
    notes = [41.2, 41.2, 49.0, 55.0]  # E1 E1 G1 A1
    k = 0; t0 = 0.0
    while t0 < total:
        i = int(t0 * SR); bar = int(k // 4)
        # kick on 1,3 ; snare on 2,4
        if k % 2 == 0:
            m = int(0.25 * SR); t = np.arange(m) / SR
            s = np.sin(2 * np.pi * (110 * np.exp(-t * 20) + 45) * t) * np.exp(-t * 12)
        else:
            m = int(0.2 * SR); t = np.arange(m) / SR
            s = fft_filter(rng.standard_normal(m).astype(np.float32), 1500, 8000) * np.exp(-t * 18) * 0.5
        j = min(n, i + m)
        if j > i: out[i:j] += s[:j - i] * 0.6
        # bass eighth notes
        f = notes[bar % 4] * 2
        for h in (0, 0.5):
            ii = int((t0 + h * beat) * SR); m = int(beat * 0.45 * SR); t = np.arange(m) / SR
            b = np.tanh(3 * np.sin(2 * np.pi * f * t)) * np.exp(-t * 4)
            jj = min(n, ii + m)
            if jj > ii: out[ii:jj] += b[:jj - ii] * 0.35
        t0 += beat; k += 1
    return out


# ---------- build ----------
def main():
    t = 0.0; lines = []; shots = []; marks = {}; sfx_track = []; voice_track = []
    for idx, item in enumerate(SEQ):
        if item[0] == 'pause':
            _, dur, cam, ex = item
            start = t; t += dur
        else:
            _, spk, text, cam, ex = item
            x = tts(spk, text, idx)
            start = t; dur = len(x) / SR
            voice_track.append((start, x))
            lines.append({'start': round(start, 3), 'end': round(start + dur, 3), 'spk': spk,
                          'text': text.replace('́', ''), 'env': lip_env(x), **ex})
            t += dur + GAP
        shots.append({'start': round(start, 3), 'end': round(t, 3), 'cam': cam, **ex})
        if 'sfx' in ex:
            sfx_track.append((start, SFX[ex['sfx']]()))
    total = t + 0.2
    n = int(total * SR)
    voice = np.zeros(n, np.float32); fx = np.zeros(n, np.float32)
    for s, x in voice_track:
        i = int(s * SR); voice[i:i + len(x)] += x[:n - i]
    for s, x in sfx_track:
        i = int(s * SR); fx[i:i + len(x)] += x[:n - i]
    mus = music(total)
    duck = 1 - 0.65 * np.clip(smooth(np.abs(voice), 8000) * 8, 0, 1)
    mix = voice * 1.0 + fx * 0.8 + mus * 0.22 * duck
    mix = mix / np.abs(mix).max() * 0.95
    write_wav(os.path.join(OUT, 'mix.wav'), mix)
    json.dump({'fps': FPS, 'duration': round(total, 3), 'lines': lines, 'shots': shots},
              open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False)
    print('total', round(total, 1), 's,', len(lines), 'lines')


if __name__ == '__main__':
    main()
