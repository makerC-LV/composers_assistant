import time
from threading import Thread

# from pyo import *
# from wx import *
import wx
from pyo import PyoGuiKeyboard, EVT_PYO_GUI_KEYBOARD

from pyo_addons.pyo_midi_server import instrument_generator, MidiSetup, run_server
from pyo_addons.sfz_instrument import sfz_voice_generator, SFZVoice, get_sfz_map

import logging
logger = logging.getLogger(__name__)

# get_sfz_map('/Users/shiva/sounds/DSKMusic/sfz')
# exit()

map = get_sfz_map('/Users/shiva/sounds/DSKMusic/sfz')

# sine = instrument_generator(4, voice_generator(SineVoice))
# INST_PROGRAMS = {1: instrument_generator(4, sfz_voice_generator('Big.sfz')), 2: sine, 3: sine, 4: sine}

INST_PROGRAMS = {i: instrument_generator(4, sfz_voice_generator(name)) for i, name in enumerate(map.keys())}

ms = MidiSetup(INST_PROGRAMS)
# map = {
#     'Classic Grand Piano': '/Users/shiva/sounds/DSKMusic/sfz/DSK Music - Classic Grand Piano/Classic Grand Piano.sfz'}

# map = {
#     'Analog Kit': '/Users/shiva/sounds/DSKMusic/sfz/DSK Music - GM Drum Kits/Analog Kit.sfz'}

# map = {
#     'Big': '/Users/shiva/sounds/DSKMusic/sfz/DSK Music - Organs/Big.sfz'}


server = run_server(ms, lambda *args: SFZVoice.read_sounds(map))

for channel in range(0, 5):
    # msg = Message('program_change', channel=channel, program=1)
    # blist = msg.bytes()
    # print(blist)
    ms.channels[channel].pchange(1)
    # server.addMidiEvent(blist[0], blist[1], 0)


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
        server.stop()
        time.sleep(0.25)
        self.Destroy()

    def onMidiNote(self, evt):
        pitch = evt.value[0]
        velocity = evt.value[1]
        print("Pitch:    %d" % pitch)
        print("Velocity: %d" % velocity)
        Thread(target=lambda *args: ms.channels[0].note_on(pitch, velocity)).start()

    def onChoice(self, event):
        name = self.choice.GetString(self.choice.GetSelection())
        program = [x for x in map.keys()].index(name)
        ms.channels[0].pchange(program)


app = wx.App(False)
mainFrame = MyFrame(None, title='Instrument Tester')
mainFrame.Show()
app.MainLoop()
