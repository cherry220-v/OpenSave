def execList(lst):
    try: return eval(lst)
    except: return []

def initAPI(api):
    global OpenFileCommand, SaveFileCommand, OpenRFileCommand, FileReadThread, FileWriteThread, addToRFiles
    VtAPI = api
    QtCore = VtAPI.importModule("PyQt6.QtCore")

    class OpenFileCommand(VtAPI.Plugin.WindowCommand):
        def __init__(self, api, window):
            super().__init__(api, window)
            self.QtCore = self.api.importModule("PyQt6.QtCore")
            self.chardet = self.api.importModule("chardet")
            self.os = self.api.importModule("os")
        def run(self, f: list = [], dlg=False):
            if dlg:
                f = self.api.Dialogs.openFileDialog()[0]
            # self.window.openFile(f) | Use command with name 'OpenFileCommand'
            for file in f:
                found = False
                for v in self.window.views:
                    if file == v.getFile():
                        self.window.focus(v)
                        found = True
                        break
                if not found:
                    view = self.window.newFile()
                    view.setFile(file)
                    self.window.setTitle(self.os.path.normpath(file))
                    view.setTitle(self.os.path.basename(file or "Untitled"))
                    self.fileReader = FileReadThread(file, self)
                    self.fileReader.line_read.connect(view.insert)
                    self.fileReader.start()
                    view.setSaved(True)
                    view.rehighlite()
                    self.window.signals.fileOpened.emit(view)

    class FileReadThread(VtAPI.Widgets.Thread):
        line_read = QtCore.pyqtSignal(str)

        def __init__(self, file_path: str, cclass, buffer_size: int = 2*1024):
            super().__init__()
            self.file_path = file_path
            self.buffer_size = buffer_size
            self._is_running = True
            self.cclass = cclass

        def run(self):
            with open(self.file_path, 'rb') as f:
                raw_data = f.read(512)
                encoding_info = self.cclass.chardet.detect(raw_data)
                encoding = encoding_info.get('encoding', 'utf-8')
            stime = 1
            with open(self.file_path, 'r', encoding=encoding, errors="ignore") as f:
                while self._is_running:
                    chunk = f.read(self.buffer_size)
                    stime += 0.1
                    if not chunk:
                        break
                    self.line_read.emit(chunk)
                    self.msleep(int(50*stime))

        def stop(self):
            self._is_running = False

    class SaveFileCommand(VtAPI.Plugin.WindowCommand):
        def __init__(self, api, window):
            super().__init__(api, window)
            self.QtCore = self.api.importModule("PyQt6.QtCore")
            self.os = self.api.importModule("os")
        def run(self, view=None, dlg=False):
            if not view:
                view = self.window.activeView
            if dlg or not view.getFile():
                f = self.api.Dialogs.saveFileDialog()[0]
            else:
                f = view.getFile()
            # self.window.saveFile(f) | Use command with name 'SaveFileCommand'
            text = view.getText()
            view.setFile(f)
            view.setTitle(self.os.path.basename(f))
            try:
                writeThread = FileWriteThread(f, text)
                writeThread.start()
                writeThread.wait()
                view.setSaved(True)
            except Exception as e:
                self.window.setLogMsg(e)

    class FileWriteThread(VtAPI.Widgets.Thread):
        def __init__(self, file_path, content, chunk_size=4096):
            super().__init__()
            self.file_path = file_path
            self.content = content
            self.chunk_size = chunk_size

        def run(self):
            try:
                total_length = len(self.content)
                written_length = 0

                with open(self.file_path, 'w', encoding='utf-8') as file:
                    for i in range(0, total_length, self.chunk_size):
                        chunk = self.content[i:i + self.chunk_size]
                        file.write(chunk)
                        written_length += len(chunk)
                        
            except Exception as e:
                print(e)

    class OpenRFileCommand(VtAPI.Plugin.WindowCommand):
        def __init__(self, api, window):
            super().__init__(api, window)
            self.os = self.api.importModule("os")
            self.ast = self.api.importModule("ast")
        def run(self):
            if not self.os.path.isfile("recent.f"):
                with open("recent.f", "a+") as f:
                    f.write("[]")
            recentFiles = open("recent.f", "r+")
            try:
                fList = self.ast.literal_eval(recentFiles.read())
            except:
                fList = []
            if len(fList) > 0 and self.window.getCommand("OpenFileCommand"):
                if fList[-1]:
                    self.window.runCommand({"command": "OpenFileCommand", "kwargs": {"f": [fList[-1]]}})
                fList.remove(fList[-1])
                recentFiles.seek(0)
                recentFiles.truncate()
                recentFiles.write(str(fList))
                recentFiles.close()
    
    def addToRFiles(view, api):
        if view.getFile():
            ast = api.importModule("ast")
            os = api.importModule("os")
            if not os.path.isfile("recent.f"):
                with open("recent.f", "a+") as f:
                    f.write("[]")
            recentFiles = open("recent.f", "r+")
            try:
                fList = ast.literal_eval(recentFiles.read())
                fList.append(view.getFile())
            except:
                fList = []
            recentFiles.seek(0)
            recentFiles.truncate()
            recentFiles.write(str(fList))
            recentFiles.close()

    VtAPI.activeWindow.signals.tabClosed.connect(lambda view: addToRFiles(view, VtAPI))
    VtAPI.activeWindow.registerCommandClass({"command": OpenRFileCommand, "shortcut": "ctrl+shift+t"})
