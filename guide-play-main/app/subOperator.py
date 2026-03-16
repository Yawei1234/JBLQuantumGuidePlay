import os
import sys
import io
import pexpect
import pexpect.popen_spawn

child = pexpect.popen_spawn.PopenSpawn("echo Hello World!")
child.wait()
child.read()
