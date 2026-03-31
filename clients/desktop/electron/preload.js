const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('sara', {
  hideWindow: () => ipcRenderer.send('hide-window'),
  micStart:   () => ipcRenderer.send('mic-start'),
  micStop:    () => ipcRenderer.send('mic-stop'),
  backendUrl: 'http://localhost:8000',
})
