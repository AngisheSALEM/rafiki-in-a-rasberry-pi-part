# Guide de test voix

Rafiki garde le depot leger : les modeles vocaux et binaires generes restent
locaux et ne sont pas commits. La sortie vocale standard utilise `espeak-ng`.
L'entree vocale PulseAudio utilise `whisper.cpp` si son binaire et son modele
sont installes localement.

## 1. Verifier les dependances

```bash
.venv/bin/python -m pip install -r requirements.txt
espeak-ng --version
parecord --version
ffmpeg -version
```

## 2. Tester la sortie vocale

```bash
espeak-ng -v fr-fr "Bonjour, je suis Rafiki."
```

Si aucune voix ne sort, verifier la sortie audio systeme avec `wpctl status`,
`pactl info` ou les reglages audio de la Raspberry Pi.

## 3. Installer les assets Whisper hors Git

Le modele par defaut attendu est :

```text
models-local/whisper/ggml-base-q5_1.bin
```

Le binaire par defaut attendu est celui du sous-module :

```text
tools/whisper.cpp/build/bin/whisper-cli
```

Ces chemins peuvent etre changes avec `--whisper-model` et
`--whisper-executable`.

## 4. Tester Rafiki en texte

```bash
.venv/bin/python scripts/talk_to_rafiki.py
```

## 5. Tester Rafiki avec micro PulseAudio

```bash
.venv/bin/python scripts/talk_to_rafiki.py \
  --input pulse \
  --pulse-device tunnel-source.tcp:10.20.20.149 \
  --whisper-model models-local/whisper/ggml-base-q5_1.bin
```

Avec le corps Arduino Mega branche en USB :

```bash
.venv/bin/python scripts/talk_to_rafiki.py \
  --input pulse \
  --pulse-device tunnel-source.tcp:10.20.20.149 \
  --whisper-model models-local/whisper/ggml-base-q5_1.bin \
  --body-driver arduino \
  --body-port /dev/ttyACM0
```

## Depannage rapide

- `moteur vocal indisponible` : installer `espeak-ng`.
- `entree vocale indisponible` : verifier `whisper-cli`, le modele Whisper,
  `parecord`, `ffmpeg` et le nom du device PulseAudio.
- `No speech recognized` : rapprocher le micro ou ajuster
  `--stt-speech-threshold` (260 par defaut).
- Le depot ne doit pas contenir de modele `.onnx`, `.bin` ou de dossier
  `tools/piper`; ces fichiers doivent rester dans `models-local/` ou etre
  installes par script sur la Raspberry.
