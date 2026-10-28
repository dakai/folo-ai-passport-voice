.pragma library

// Panel copy in the two languages this project is documented in.
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
  }
}

function lang(override, localeName) {
  var forced = String(override || "")
  if (forced === "en" || forced === "zh") return forced
  var name = String(localeName || "").toLowerCase()
  return name.indexOf("zh") === 0 ? "zh" : "en"
}

function text(langCode, key) {
  var table = STRINGS[langCode] || STRINGS.en
  return table[key] !== undefined ? table[key] : key
}
