# Eye Rest

An offline GNOME/X11 eye-break app. Every 20 minutes it covers all connected
monitors for 20 seconds. Look at something at least 20 feet (6 metres) away
and blink fully and often. There are no skip, snooze, or settings controls.
The app cannot detect gaze or blinking. A system bell marks the end; whether
it is audible depends on your desktop sound settings.

Guidance:
- https://www.aao.org/eye-health/glasses-contacts/computer-usage
- https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome

## Setup

On Ubuntu, install the GTK 3 bindings and run the app from the repository
in a GNOME on Xorg session.

```sh
sudo apt install python3-gi gir1.2-gtk-3.0
/usr/bin/python3 eye_rest.py
```

To preview one 20-second break, stop any running instance and run
`/usr/bin/python3 eye_rest.py --preview`.

## Start at login

Create `~/.config/autostart/eye-rest.desktop` with the following contents.
Replace the example path with the absolute path to your checkout.

```ini
[Desktop Entry]
Type=Application
Name=Eye Rest
Exec=/usr/bin/python3 "/absolute/path/to/eye-rest/eye_rest.py"
```

## Usage

There is no in-app exit shortcut. During breaks the app captures keyboard
and pointer input, retrying if the initial capture fails. Desktop and system
shortcuts may still take priority; this is not an OS security boundary.
Use Ctrl+C in the terminal that launched the app. For an instance started
at login, find its PID with `pgrep -af '[/]usr/bin/python3 .*/eye_rest.py'`
and run `kill PID` with the matching PID.
Remove the autostart desktop file to stop launch at login. It deliberately
does not prevent OS-level process termination or change system privileges.

The timer resets after a detected sleep/resume gap. It otherwise counts
elapsed time, including time while the desktop is idle or locked. It does
not monitor activity or use a camera. A first break occurs 20 minutes after
startup. No network access, additional Python packages, or telemetry.
