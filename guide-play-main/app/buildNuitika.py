from nutikacompile import compile_with_nuitka
# creates the command line and executes it in a new console
wholecommand = compile_with_nuitka(
    pyfile=r".\app\guiBeta.py",
    icon=r".\app\assets\app-icon.ico",
    disable_console=True,
    file_version="1.0.0.10",
    onefile=False,
    outputdir=r".\app\dist\guide-play\Dist2",
    # addfiles=[
    #     r"C:\ProgramData\anaconda3\envs\adda\convertpic2ico.exe",  # output: compiledapptest/convertpic2ico.exe
    #     r"C:\ProgramData\anaconda3\envs\adda\pi2\README.MD",  # output: compiledapptest/pi2/README.MD
    # ],
    delete_onefile_temp=False,  # creates a permanent cache folder
    needs_admin=True,
)
print(wholecommand)
