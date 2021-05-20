from pyo import Sine

from pyo_addons.embedded_pyo_synth import Voice


class SineVoice(Voice):
    def __init__(self, debug=False):
        super().__init__('SineVoice', debug=debug)
        self.sn = Sine(freq=self.get_freq(), mul=self.get_amplitude())
        self.output = self.sn

    def play(self):
        self.sn.freq = self.get_freq()
        self.sn.mul = self.get_amplitude()
        super().play()

    def stop(self):
        super().stop()

    @classmethod
    def get_instance(cls):
        return SineVoice()
