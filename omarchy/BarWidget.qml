import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "I18n.js" as I18n

// Bar entry point: a microphone whose colour is the service state, plus the
// host for Panel.qml. Icon only — the panel carries the words.
//
// The widget owns no settings beyond where the checkout lives. Everything it
// displays comes from `voice_tui.py status --json`, which reads the same
// voice-config.json the forwarder reads — so the terminal configurator, this
// panel and the running service cannot drift apart.
BarWidget {
  id: root
  moduleName: "manchunx7.ai-passport-voice"

  // nf-fa-microphone / nf-fa-power_off. The slashed microphone is deliberately
  // unused: it reads as "muted", and this widget has no mute state — it means
  // "the service is not running", which a power glyph says without ambiguity.
  readonly property string glyphOn: "\uf130"
  readonly property string glyphOff: "\uf011"

  readonly property string pluginDir: {
    var url = Qt.resolvedUrl(".").toString()
    if (url.indexOf("file://") === 0) url = url.substring(7)
    if (url.length > 1 && url.charAt(url.length - 1) === "/")
      url = url.substring(0, url.length - 1)
    return decodeURIComponent(url)
  }

  readonly property string lang: I18n.lang(root.setting("language", "auto"), Qt.locale().name)
  readonly property string repoPath: String(root.setting("repoPath", "") || "")

  function t(key) { return I18n.text(root.lang, key) }

  // Parsed `status --json`. Empty until the first poll lands.
  property var status: ({})
  property string statusJson: ""
  property string helperError: ""

  readonly property bool serviceActive: root.status.active === true
  readonly property string link: String(root.status.link || "unknown")
  readonly property bool linked: root.link === "linked"

  // colours.toml ships a `green`, but Commons.Color exposes only foreground,
  // accent, urgent and muted — so read the one palette value the shell drops.
  // Read once at load, exactly like Color.qml reads its own file: a theme
  // switch pushes the four known roles through IPC and restarts nothing.
  property string themeGreen: ""

  readonly property color connectedColor: root.themeGreen !== ""
    ? root.themeGreen : "#9ece6a"   // fallback: Tokyo Night green

  // Grey for "running, nothing connected": the microphone only earns full
  // colour once a device is actually there. Alpha rather than Color.muted,
  // which is near-invisible on a dark bar.
  readonly property color idleColor: Util.alpha(
    root.bar ? root.bar.barForeground : Commons.Color.foreground, 0.55)

  function parseGreen(raw) {
    var match = String(raw || "").match(/^\s*green\s*=\s*["']?(#[0-9A-Fa-f]{6})/m)
    return match ? match[1] : ""
  }
  readonly property var llm: root.status.llm || ({})

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true : false

  function helper() {
    var base = [root.pluginDir + "/bin/aipv"]
    if (root.repoPath !== "") {
      base.push("--repo")
      base.push(root.repoPath)
    }
    return base
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function applyStatus(text) {
    if (!text) return
    try {
      var parsed = JSON.parse(text)
      if (parsed && typeof parsed === "object") {
        root.status = parsed
        root.statusJson = text
        root.helperError = ""
      }
    } catch (e) {
      root.helperError = "status output unreadable"
    }
  }

  function stateText() {
    if (root.helperError !== "") return root.helperError
    if (root.status.active === undefined) return root.t("stateLoading")
    if (!root.serviceActive) return root.t("stateDown")
    return root.linked ? root.t("stateLinked") : root.t("stateWaiting")
  }

  function llmText() {
    if (root.llm.enabled === true)
      return String(root.llm.providerLabel || "") + " · " + String(root.llm.model || "")
    return root.t("llmOff")
  }

  function open() {
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function togglePanel() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = button
    if ("hostWidget" in target) target.hostWidget = root
    if ("host" in target) target.host = root
    if ("helper" in target) target.helper = root.helper()
    if ("connectedColor" in target) target.connectedColor = root.connectedColor
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: {
    injectPanel()
    refresh()
  }
  onSettingsChanged: injectPanel()

  // 10 s: the dot is worth keeping current, and one short python process per
  // tick is cheaper than watching the journal. The panel forces a refresh on
  // open, so this only has to be good enough for the resting bar.
  FileView {
    id: themeColors
    path: Commons.Color.currentThemePath + "/colors.toml"
    watchChanges: false
    printErrors: false
    onLoaded: root.themeGreen = root.parseGreen(text())
  }

  Timer {
    interval: 10000
    repeat: true
    running: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Process {
    id: statusProc
    // --lang: provider labels come from the configurator, so the panel's
    // language has to reach it rather than being translated twice.
    command: root.helper().concat(["status", "--json", "--lang", root.lang])
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var message = String(text || "").trim()
        if (message.length > 0) root.helperError = message.split("\n")[0]
      }
    }
  }

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  IpcHandler {
    target: "manchunx7.ai-passport-voice"

    // Headless truth source: `omarchy-shell manchunx7.ai-passport-voice probe`
    // prints the parsed status instead of requiring a screenshot.
    function probe(): string {
      root.refresh()
      return root.statusJson !== "" ? root.statusJson : root.helperError
    }
    function refresh(): void { root.refresh() }
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.togglePanel() }
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.serviceActive ? root.glyphOn : root.glyphOff
    // Colour carries the state: 45% opacity + power glyph = service down,
    // grey microphone = running and waiting, theme green = device connected.
    foreground: root.serviceActive
      ? root.idleColor
      : (root.bar ? root.bar.barForeground : Commons.Color.foreground)
    active: root.serviceActive && root.linked
    activeColor: root.connectedColor
    dimmed: !root.serviceActive
    tooltipText: "AI Passport · " + root.stateText() + " · " + root.llmText()
    onPressed: function (buttonCode) {
      if (buttonCode === Qt.RightButton) root.refresh()
      else root.togglePanel()
    }
  }
}
