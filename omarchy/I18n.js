.pragma library

// Panel copy in the four languages this project ships tables for.
//
// Qt.locale() inside a layer-shell widget follows the shell process's LANG, not
// a desktop preference, so the language is resolved from the locale name with an
// explicit override in the widget settings for the case where a mostly-English
// desktop should still speak Chinese (or the reverse).
var STRINGS = {
  en: {
    title: "AI Passport voice",
    stateLoading: "reading status…",
    stateDown: "service not running",
    stateWaiting: "waiting for device",
    stateLinked: "device connected",
    serviceRunning: "ai-passport-voice.service running",
    serviceStopped: "ai-passport-voice.service not running",
    last: "Last",
    llmTitle: "LLM cleanup (fillers, punctuation)",
    llmOff: "off: the raw transcript is typed",
    provider: "Provider",
    model: "Model",
    fetchModels: "Fetch the model list from the endpoint",
    modelHint: "Press ↻ to fetch models, or: voice_tui.py set --model <name>",
    keyNewKeyring: "API key · will be stored in the login keyring",
    keyNewFile: "API key · no secret-tool, will be stored in the config file",
    keyStoredKeyring: "Key saved in the login keyring · type a new one to replace",
    keyStoredFile: "Key saved in plain text · type it again to move it to the keyring",
    keyStoredEnv: "Key comes from AIPV_API_KEY · typing stores a copy",
    keyFileWarning: "Key is plain text in voice-config.json — re-enter it once to move it into the keyring",
    modelPick: "Select a model",
    modelSearch: "Search models…",
    modelEmpty: "No matches",
    fetchingModels: "fetching models…",
    modelsFound: "{count} models",
    modelsNone: "no models returned",
    savedNote: "saved · applies immediately",
    saving: "saving…",
    savingKey: "saving key…",
    noteDefault: "Changes apply immediately, no restart. Terminal: linux/voice_tui.py",
    waitingTip: "Open \u201cAI voice\u201d on the device, then hold the top button to talk",
    tipServiceDown: "Service is not running. Start it:\n" +
      "systemctl --user start ai-passport-voice.service\n" +
      "First install: bash linux/install.sh",
    actionStart: "Start the forwarder service",
    actionRestart: "Restart the forwarder service",
    restarting: "restarting…",
    starting: "starting…",
    failed: "failed"
  },
  zh: {
    title: "AI Passport 语音",
    stateLoading: "读取中…",
    stateDown: "服务未运行",
    stateWaiting: "等待设备",
    stateLinked: "已连接设备",
    serviceRunning: "ai-passport-voice.service 运行中",
    serviceStopped: "ai-passport-voice.service 未运行",
    last: "最近",
    llmTitle: "LLM 整理 (去口头语/补标点)",
    llmOff: "关闭: 只键入本地识别原文",
    provider: "Provider",
    model: "模型",
    fetchModels: "从端点获取模型列表",
    modelHint: "点 ↻ 取模型列表, 或: voice_tui.py set --model <名字>",
    keyNewKeyring: "API key · 将存入登录密钥环",
    keyNewFile: "API key · 未装 secret-tool, 将写入配置文件",
    keyStoredKeyring: "Key 已在登录密钥环 · 输入新 key 覆盖",
    keyStoredFile: "Key 以明文保存 · 重新输入一次移入密钥环",
    keyStoredEnv: "Key 来自 AIPV_API_KEY · 输入则另存一份",
    keyFileWarning: "Key 以明文存在 voice-config.json — 重新输入一次即可移入密钥环",
    modelPick: "选择模型",
    modelSearch: "搜索模型…",
    modelEmpty: "没有匹配",
    fetchingModels: "获取模型中…",
    modelsFound: "取到 {count} 个模型",
    modelsNone: "没有取到模型",
    savedNote: "已保存 · 立即生效",
    saving: "保存中…",
    savingKey: "保存 key…",
    noteDefault: "改动即时生效, 无需重启。终端里也可以: linux/voice_tui.py",
    waitingTip: "在设备上打开「AI 语音」, 按住上键说话",
    tipServiceDown: "服务未运行。启动:\n" +
      "systemctl --user start ai-passport-voice.service\n" +
      "首次安装: bash linux/install.sh",
    actionStart: "启动转发器服务",
    actionRestart: "重启转发器服务",
    restarting: "重启中…",
    starting: "启动中…",
    failed: "失败"
  },
  es: {
    title: "Voz de AI Passport",
    stateLoading: "leyendo estado…",
    stateDown: "servicio detenido",
    stateWaiting: "esperando dispositivo",
    stateLinked: "dispositivo conectado",
    serviceRunning: "ai-passport-voice.service en marcha",
    serviceStopped: "ai-passport-voice.service detenido",
    last: "Último",
    llmTitle: "Limpieza con LLM (muletillas, puntuación)",
    llmOff: "desactivada: se escribe la transcripción original",
    provider: "Proveedor",
    model: "Modelo",
    fetchModels: "Obtener la lista de modelos del endpoint",
    modelHint: "Pulsa ↻ para obtener modelos, o: voice_tui.py set --model <nombre>",
    keyNewKeyring: "API key · se guardará en el llavero de sesión",
    keyNewFile: "API key · sin secret-tool, se guardará en el archivo de configuración",
    keyStoredKeyring: "Clave guardada en el llavero · escribe otra para reemplazarla",
    keyStoredFile: "Clave guardada en texto claro · vuelve a escribirla para moverla al llavero",
    keyStoredEnv: "La clave viene de AIPV_API_KEY · escribirla guarda una copia",
    keyFileWarning: "La clave está en claro en voice-config.json — vuelve a introducirla una vez para moverla al llavero",
    modelPick: "Elegir un modelo",
    modelSearch: "Buscar modelos…",
    modelEmpty: "Sin coincidencias",
    fetchingModels: "obteniendo modelos…",
    modelsFound: "{count} modelos",
    modelsNone: "el endpoint no devolvió modelos",
    savedNote: "guardado · se aplica al instante",
    saving: "guardando…",
    savingKey: "guardando clave…",
    noteDefault: "Los cambios se aplican al instante, sin reiniciar. Terminal: linux/voice_tui.py",
    waitingTip: "Abre «AI voice» en el dispositivo y mantén pulsado el botón superior para hablar",
    tipServiceDown: "El servicio no está en marcha. Inícialo:\n" +
      "systemctl --user start ai-passport-voice.service\n" +
      "Primera instalación: bash linux/install.sh",
    actionStart: "Iniciar el servicio del forwarder",
    actionRestart: "Reiniciar el servicio del forwarder",
    restarting: "reiniciando…",
    starting: "iniciando…",
    failed: "falló"
  },
  ja: {
    title: "AI Passport 音声",
    stateLoading: "状態を読み込み中…",
    stateDown: "サービス停止中",
    stateWaiting: "デバイス待ち",
    stateLinked: "デバイス接続済み",
    serviceRunning: "ai-passport-voice.service 稼働中",
    serviceStopped: "ai-passport-voice.service 停止中",
    last: "最近",
    llmTitle: "LLM 整形 (フィラー・句読点)",
    llmOff: "オフ: 認識した原文をそのまま入力",
    provider: "プロバイダー",
    model: "モデル",
    fetchModels: "エンドポイントからモデル一覧を取得",
    modelHint: "↻ でモデルを取得、または: voice_tui.py set --model <名前>",
    keyNewKeyring: "API key · ログインキーリングに保存します",
    keyNewFile: "API key · secret-tool が無いため設定ファイルに保存します",
    keyStoredKeyring: "キーはログインキーリングに保存済み · 新しいキーで置き換え",
    keyStoredFile: "キーは平文で保存済み · もう一度入力するとキーリングへ移ります",
    keyStoredEnv: "キーは AIPV_API_KEY から取得 · 入力すると複製を保存",
    keyFileWarning: "キーが voice-config.json に平文であります — 一度入力し直すとキーリングへ移ります",
    modelPick: "モデルを選択",
    modelSearch: "モデルを検索…",
    modelEmpty: "一致なし",
    fetchingModels: "モデルを取得中…",
    modelsFound: "{count} 個のモデル",
    modelsNone: "モデルが返されませんでした",
    savedNote: "保存しました · すぐ反映",
    saving: "保存中…",
    savingKey: "キーを保存中…",
    noteDefault: "変更は再起動なしで反映されます。ターミナル: linux/voice_tui.py",
    waitingTip: "デバイスで「AI 语音」を開き、上ボタンを押したまま話してください",
    tipServiceDown: "サービスが動いていません。起動:\n" +
      "systemctl --user start ai-passport-voice.service\n" +
      "初回インストール: bash linux/install.sh",
    actionStart: "フォワーダーサービスを起動",
    actionRestart: "フォワーダーサービスを再起動",
    restarting: "再起動中…",
    starting: "起動中…",
    failed: "失敗"
  }
}

function lang(override, localeName) {
  var forced = String(override || "")
  if (STRINGS[forced]) return forced
  var name = String(localeName || "").toLowerCase()
  for (var code in STRINGS) {
    if (name.indexOf(code) === 0) return code
  }
  return "en"
}

function text(langCode, key) {
  var table = STRINGS[langCode] || STRINGS.en
  return table[key] !== undefined ? table[key] : key
}
