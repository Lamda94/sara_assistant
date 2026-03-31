const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage, screen, ipcMain } = require('electron')
const path = require('path')

const isDev = process.env.NODE_ENV === 'development'
const BACKEND_URL = 'http://localhost:8000'

let win = null
let tray = null
let isVisible = false

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  win = new BrowserWindow({
    width: 420,
    height: 580,
    x: Math.floor(width / 2 - 210),
    y: Math.floor(height / 2 - 290),
    frame: false,
    backgroundColor: '#1A1C1E',
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Conceder acceso al micrófono (necesario para Web Speech API)
  win.webContents.session.setPermissionRequestHandler(
    (_wc, permission, callback) => callback(permission === 'media')
  )
  win.webContents.session.setPermissionCheckHandler(
    (_wc, permission) => permission === 'media'
  )

  if (isDev) {
    win.loadURL('http://localhost:5173').catch(() => {
      win.loadURL('http://localhost:5174')
    })
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  win.webContents.on('did-fail-load', (_, code, desc, url) => {
    if (isDev) setTimeout(() => win.reload(), 1000)
  })

  // Ocultar cuando pierde el foco (excepto si hay IPC diciendo que el mic está activo)
  let micActive = false
  ipcMain.on('mic-start', () => { micActive = true })
  ipcMain.on('mic-stop',  () => { micActive = false })

  win.on('blur', () => {
    if (isVisible && !micActive) hideWindow()
  })
}

function showWindow() {
  if (!win) return
  win.show()
  win.focus()
  isVisible = true
}

function hideWindow() {
  if (!win) return
  win.hide()
  isVisible = false
}

function toggleWindow() {
  isVisible ? hideWindow() : showWindow()
}

function createTray() {
  // Ícono simple de 16x16 en base64 (punto cian)
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABOSURBVDiNY/z//z8DMpYhBqhgZGT8z0BFwCgNhmFgYGBguHnz5n8yNY9RGgzDwMDAwHDz5s3/ZGoeo7QGgzAwMDAw3Lx58z+ZmgcAi3AQVZ2LHQAAAABJRU5ErkJggg=='
  )
  tray = new Tray(icon)
  tray.setToolTip('SARA — Ctrl+Space para abrir')

  const menu = Menu.buildFromTemplate([
    { label: 'Mostrar SARA', click: showWindow },
    { type: 'separator' },
    { label: 'Salir', click: () => app.quit() },
  ])

  tray.setContextMenu(menu)
  tray.on('click', toggleWindow)
}

app.commandLine.appendSwitch('disable-web-security')
app.commandLine.appendSwitch('allow-insecure-localhost')

app.whenReady().then(() => {
  createWindow()
  createTray()
  ipcMain.on('hide-window', hideWindow)

  // Atajo global Ctrl+Space
  globalShortcut.register('CommandOrControl+Space', toggleWindow)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', (e) => {
  // Evitar que la app cierre al cerrar la ventana
  e.preventDefault()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
