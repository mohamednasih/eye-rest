#!/usr/bin/python3
"""Local, offline eye-break reminder for GNOME/X11."""
import argparse
import fcntl
import math
import os
from pathlib import Path
import signal
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk

INTERVAL = 20 * 60
DURATION = 20


class Schedule:
    def __init__(self, now, interval=INTERVAL):
        self.interval = interval
        self.last = now
        self.due = now + interval

    def ready(self, now):
        # A suspended machine already gives the eyes time away from its screen.
        if now - self.last > 60:
            self.due = now + self.interval
        self.last = now
        return now >= self.due

    def completed(self, now):
        self.last = now
        self.due = now + self.interval


class EyeRest:
    def __init__(self, preview=False):
        self.schedule = Schedule(time.monotonic())
        self.windows = []
        self.labels = []
        self.seat = None
        self.grabbed = False
        self.end = None
        self.preview = preview
        css = Gtk.CssProvider()
        css.load_from_data(b'''
            window { background: #101e25; color: #e4efe9; }
            .eyebrow { color: #86c4ae; font-size: 17px; letter-spacing: 3px; }
            .title { font-size: 44px; font-weight: bold; }
            .body { font-size: 23px; color: #c4d7d0; }
            .timer { font-size: 72px; font-weight: 300; color: #a8dbc5; }
            .foot { font-size: 13px; color: #8baba2; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        GLib.timeout_add(250, self.tick)
        if preview:
            GLib.idle_add(self.start_break)

    def label(self, box, text, style):
        label = Gtk.Label(label=text)
        label.get_style_context().add_class(style)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 9)
        return label

    def start_break(self):
        if self.windows:
            return False
        display = Gdk.Display.get_default()
        self.end = time.monotonic() + DURATION
        for index in range(display.get_n_monitors()):
            monitor = display.get_monitor(index)
            geometry = monitor.get_geometry()
            window = Gtk.Window(title='Eye Rest — look away')
            window.set_decorated(False)
            window.set_keep_above(True)
            window.set_skip_taskbar_hint(True)
            window.set_skip_pager_hint(True)
            window.set_accept_focus(True)
            window.move(geometry.x, geometry.y)
            window.set_default_size(geometry.width, geometry.height)
            window.connect('delete-event', lambda *_: True)
            window.connect('key-press-event', self.key)
            window.connect('grab-broken-event', self.grab_broken)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            outer.set_valign(Gtk.Align.CENTER)
            outer.set_halign(Gtk.Align.CENTER)
            outer.set_margin_start(24)
            outer.set_margin_end(24)
            window.add(outer)
            self.label(outer, 'A MOMENT FOR YOUR EYES', 'eyebrow')
            self.label(outer, 'Look into the distance.', 'title')
            self.label(outer, 'Choose something at least 6 metres / 20 feet away.\nBlink gently and fully. Let your eyes relax.', 'body')
            self.labels.append(self.label(outer, '20', 'timer'))
            self.label(outer, 'You don’t need to watch the countdown. A soft tone marks the end.', 'body')
            self.label(outer, '20 seconds away, every 20 minutes · AAO / AOA guidance', 'foot')
            window.show_all()
            window.fullscreen_on_monitor(Gdk.Screen.get_default(), index)
            self.windows.append(window)
        self.windows[0].present()
        self.seat = display.get_default_seat()
        # Window mapping is asynchronous. Retry capture from the timer if the
        # window is not viewable yet or another client currently holds a grab.
        GLib.idle_add(self.capture_input)
        return False

    def capture_input(self):
        if self.windows and self.seat and not self.grabbed:
            window = self.windows[0]
            if window.get_mapped():
                window.present()
                status = self.seat.grab(
                    window.get_window(),
                    Gdk.SeatCapabilities.KEYBOARD | Gdk.SeatCapabilities.ALL_POINTING,
                    False, None, None, None, None)
                self.grabbed = status == Gdk.GrabStatus.SUCCESS
        return False

    def grab_broken(self, _window, _event):
        self.grabbed = False
        return False

    def key(self, _window, event):
        return True

    def clear(self):
        if self.seat:
            self.seat.ungrab()
            self.seat = None
        self.grabbed = False
        for window in self.windows:
            window.destroy()
        self.windows.clear()
        self.labels.clear()

    def stop(self, *_):
        self.clear()
        Gtk.main_quit()

    def tick(self):
        now = time.monotonic()
        if self.windows:
            remaining = max(0, math.ceil(self.end - now))
            if remaining:
                self.capture_input()
            for label in self.labels:
                label.set_text(str(remaining))
            if remaining == 0:
                Gdk.Display.get_default().beep()
                self.clear()
                self.schedule.completed(now)
                if self.preview:
                    self.stop()
                    return False
        elif self.schedule.ready(now):
            self.start_break()
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Show one real 20-second break, then exit')
    args = parser.parse_args()
    initialized, _ = Gtk.init_check()
    if not initialized:
        print('Eye Rest cannot connect to the desktop. Launch Eye Rest from your desktop Applications menu.', file=sys.stderr)
        return 1
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', str(Path.home() / '.cache')))
    runtime.mkdir(parents=True, exist_ok=True)
    lock = open(runtime / 'eye-rest.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Eye Rest is already running.')
        return
    app = EyeRest(args.preview)
    signal.signal(signal.SIGTERM, app.stop)
    signal.signal(signal.SIGINT, app.stop)
    Gtk.main()


if __name__ == '__main__':
    sys.exit(main())
