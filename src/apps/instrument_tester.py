import logging
import time
from threading import Thread

# from pyo import *
# from wx import *
import wx
from pyo import PyoGuiKeyboard, EVT_PYO_GUI_KEYBOARD

from pyo_addons.embedded_pyo_synth import instrument_generator, PyoSynth
from pyo_addons.sfz_instrument import sfz_voice_generator, SFZVoice, get_sfz_map_from_config, \
    read_sfz_config

logger = logging.getLogger(__name__)

pyo_synth = None
map = None


class MyFrame(wx.Frame):

    def __init__(self, parent, title, pos=(50, 50), size=(1000, 200)):
        wx.Frame.__init__(self, parent, -1, title, pos, size)

        self.Bind(wx.EVT_CLOSE, self.on_quit)

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.VERTICAL)

        # vmainsizer = wx.BoxSizer(wx.VERTICAL)

        chlbl = wx.StaticText(panel, label="Choose instrument", style=wx.ALIGN_CENTRE)

        instruments = list(map.keys())
        self.choice = wx.Choice(panel, choices=instruments)
        self.choice.Bind(wx.EVT_CHOICE, self.onChoice)

        keyboard = PyoGuiKeyboard(panel)
        keyboard.Bind(EVT_PYO_GUI_KEYBOARD, self.onMidiNote)

        box.Add(chlbl, 0, wx.EXPAND | wx.ALL, 5)
        box.Add(self.choice, 1, wx.EXPAND | wx.ALL, 5)

        box.AddStretchSpacer()

        box.Add(keyboard, 5, wx.ALL | wx.EXPAND, 5)

        # vmainsizer.Add(choice, 1, wx.ALL | wx.EXPAND, 5)
        # vmainsizer.Add(keyboard, 5, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(box)

    def on_quit(self, evt):
        pyo_synth.stop()
        time.sleep(0.25)
        self.Destroy()

    def onMidiNote(self, evt):
        pitch = evt.value[0]
        velocity = evt.value[1]
        print("Pitch:    %d" % pitch)
        print("Velocity: %d" % velocity)
        Thread(target=lambda *args: pyo_synth.note_on(pitch, 0, velocity)).start()

    def onChoice(self, event):
        name = self.choice.GetString(self.choice.GetSelection())
        program = [x for x in map.keys()].index(name)
        pyo_synth.program_change(0, program)


if __name__ == '__main__':
    # Alternate PyoSynth config
    # sine = instrument_generator(4, voice_generator(SineVoice))
    # INST_PROGRAMS = {1: sine, 2: sine, 3: sine, 4: sine}

    # Configure PyoSynth here
    map = get_sfz_map_from_config('../config/dskconfig.json')
    INST_PROGRAMS = {i: instrument_generator(4, sfz_voice_generator(name)) for i, name in enumerate(map.keys())}
    PyoSynth.configure(INST_PROGRAMS, lambda *args: SFZVoice.read_sounds(map))
    PyoSynth.configure_instrument_map(read_sfz_config('../config/dskconfig.json'))

    # Needs to be global so it doesn't get garbage collected
    pyo_synth = PyoSynth()
    pyo_synth.program_change(0, 0)

    app = wx.App(False)
    mainFrame = MyFrame(None, title='Instrument Tester')
    mainFrame.Show()
    app.MainLoop()
