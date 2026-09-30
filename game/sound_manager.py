import math
import random
from array import array

import pygame


class SoundManager:
    """Sound effects for the game.

    No audio files or extra packages are needed: the effects are synthesized at
    startup with the standard library and played through pygame.mixer.
    If no audio device is available the manager silently disables itself, so
    the game still runs normally.
    """

    def __init__(self, volume=0.6):
        self.enabled = False
        self.sounds = {}
        self.volume = volume

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1)
            freq, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:  # generator below writes 16-bit signed samples
                return
            self._rate, self._channels = freq, channels
            self.sounds = {
                "slice": self._make_slice(),
                "bomb": self._make_bomb(),
                "game_over": self._make_game_over(),
            }
            for snd in self.sounds.values():
                snd.set_volume(self.volume)
            self.enabled = True
        except (pygame.error, NotImplementedError):
            self.enabled = False

    # ---------- playback ----------

    def play(self, name, queue_after=None):
        """Play a named effect. Returns the Channel (or None).

        If queue_after (a Channel) is given, the sound is queued to start when
        that channel's current sound finishes instead of overlapping it.
        """
        if not self.enabled:
            return None
        snd = self.sounds[name]
        if queue_after is not None and queue_after.get_busy():
            queue_after.queue(snd)
            return queue_after
        return snd.play()

    # ---------- synthesis helpers ----------

    def _build(self, samples):
        """Turn a list of floats in [-1, 1] into a pygame Sound (mono or stereo)."""
        data = array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            for _ in range(self._channels):
                data.append(v)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _tone(self, f0, f1, dur, amp=1.0, noise=0.0, decay=4.0):
        """Sine sweep from f0 to f1 Hz with optional noise and exponential decay."""
        n = int(self._rate * dur)
        out, phase = [], 0.0
        for i in range(n):
            t = i / n
            phase += 2 * math.pi * (f0 + (f1 - f0) * t) / self._rate
            env = math.exp(-decay * t) * min(1.0, i / 80)  # short attack avoids clicks
            s = math.sin(phase) * (1 - noise) + random.uniform(-1, 1) * noise
            out.append(s * env * amp)
        return out

    def _make_slice(self):
        # Quick "swish": noisy rising chirp
        return self._build(self._tone(700, 1800, 0.14, amp=0.8, noise=0.45, decay=5.0))

    def _make_bomb(self):
        # Low boom: falling rumble with lots of noise
        return self._build(self._tone(140, 35, 0.6, amp=1.0, noise=0.5, decay=3.5))

    def _make_game_over(self):
        # Sad descending four-note phrase
        samples = []
        for f in (392.0, 330.0, 262.0, 196.0):
            samples += self._tone(f, f * 0.98, 0.22, amp=0.7, decay=2.5)
        samples += self._tone(196.0, 180.0, 0.45, amp=0.7, decay=3.0)
        return self._build(samples)
