#!/usr/bin/env python3
"""
Слушатель аудио. Активирует модуль audio_voice при произнесении имени
или при необходимости работы с аудиофайлом.
Требует: pip install SpeechRecognition pyaudio (или sounddevice)
"""

import time
import threading
from pathlib import Path

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False
    print("[Audio] SpeechRecognition не установлен. Аудио-активация отключена.")


class AudioListener:
    def __init__(self, core, wake_words=None):
        self.core = core
        self.wake_words = wake_words or ["блок", "ассистент", "эй"]
        self.running = False
        self.recognizer = sr.Recognizer() if HAS_SR else None
        self.microphone = sr.Microphone() if HAS_SR else None

    def start(self):
        if not HAS_SR:
            return
        self.running = True
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()
        print("[Audio] Слушатель запущен. Скажите имя для активации.")

    def stop(self):
        self.running = False

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        while self.running:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio, language="ru-RU").lower()
                print(f"[Audio] Услышал: {text}")

                if any(w in text for w in self.wake_words):
                    # Активируем модуль аудио/голоса
                    self.core.process(f"голосовая команда: {text}")
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"[Audio] Ошибка: {e}")
                time.sleep(1)
