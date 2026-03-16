import os
import sys
import subprocess
import re
from subprocess import Popen, PIPE, DEVNULL

# This function will check if the process is already running or not


def get_running_processes(look_for='', pid=None, add_exe=True):
    # TODO: Linux implementation
    cmd = f'tasklist /NH'
    if look_for:
        if not look_for.endswith('.exe') and add_exe:
            look_for += '.exe'
        cmd += f' /FI "IMAGENAME eq {look_for}"'
    if pid is not None:
        cmd += f' /FI "PID eq {pid}"'
    p = Popen(cmd, shell=True, stdout=PIPE, stdin=DEVNULL,
              stderr=DEVNULL, text=True, encoding='iso8859-2', close_fds=True)
    p.stdout.readline()
    for task in iter(lambda: p.stdout.readline().strip(), ''):
        m = re.match(r'(.+?) +(\d+) (.+?) +(\d+) +(\d+.* K).*', task)
        if m is not None:
            yield {'name': m.group(1), 'pid': int(m.group(2)), 'session_name': m.group(3),
                   'session_num': m.group(4), 'mem_usage': m.group(5)}


count = 0
for process in get_running_processes("guide-play.exe"):
    print(process)
    if process['name'] == 'guide-play.exe':
        count += 1
        if count > 1:
            print('Process is already running')
            sys.exit(0)
    pass
