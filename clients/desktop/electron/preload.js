const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('sara', {
  hideWindow: () => ipcRenderer.send('hide-window'),
  backendUrl: 'http://localhost:8000',
})
