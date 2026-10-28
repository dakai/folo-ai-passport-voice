import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "I18n.js" as I18n

// The voice panel: backend status on top, LLM cleanup settings below.
//
// All state is read from the host widget's `status` (one `voice_tui.py status
// --json` call per poll) and every change is written by running the same
// configurator with `set …`. Nothing is persisted in shell.json, so the
// terminal tool stays the single source of truth.
Panel {
  id: root
  moduleName: "manchunx7.ai-passport-voice"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property var host: null
  property var helper: []

  readonly property string lang: I18n.lang(root.setting("language", "auto"), Qt.locale().name)
  function t(key) { return I18n.text(root.lang, key) }

  readonly property var status: root.host ? root.host.status : ({})
  readonly property var llm: root.status.llm || ({})
  readonly property var providers: root.status.providers || []
  readonly property bool serviceActive: root.status.active === true
  readonly property string link: String(root.status.link || "unknown")
  readonly property string lastError: String(root.status.lastError || "")
  readonly property string lastText: String(root.status.lastText || "")
  readonly property string provider: String(root.llm.provider || "off")
  readonly property bool customProvider: root.provider === "custom"
  readonly property bool switchOn: root.llm.switchOn === true
  readonly property string keyStorage: String(root.llm.keyStorage || "none")

  readonly property string fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
  // Panel content uses the theme foreground: barForeground can switch to a
  // wallpaper-contrast colour, which does not follow the popup surface.
  readonly property color foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
  readonly property color dim: Qt.darker(root.foreground, 1.45)
  readonly property color urgentColor: root.bar ? root.bar.urgent : Commons.Color.urgent
  // Injected by the widget: the theme's green, which Commons.Color does not
  // expose. Falls back to accent so the dot is never invisible.
  property color connectedColor: Commons.Color.accent

  // Fetched on demand: listing models costs a request, and a local server may
  // take a second to answer.
  property var modelOptions: []
  // Which provider `modelOptions` belongs to: a list fetched for OpenRouter is
  // not a list for Ollama, and showing it would offer models that cannot serve.
  property string modelsFor: ""
  // Providers whose model list already failed this session (a gateway can
  // serve /chat/completions and still 401 on /models). Retried only by ↻ or a
  // provider change, not on every panel open.
  property string modelsFailedFor: ""
  property string note: ""
  property string keyDraft: ""

  function open() {
    root.refresh()
    root.maybeFetchModels()
    root.controller.show()
  }

  function close() {
    root.controller.hide()
  }

  function refresh() {
    if (root.host) root.host.refresh()
  }

  function providerOptions() {
    var out = []
    for (var i = 0; i < root.providers.length; i++)
      out.push({ value: String(root.providers[i].id), label: String(root.providers[i].label) })
    return out
  }

  function run(proc, args) {
    if (proc.running) return
    // --lang: the configurator's own lines are echoed back into the note here,
    // so it has to speak the panel's language, not the shell's.
    proc.command = root.helper.concat(args).concat(["--lang", root.lang])
    proc.running = true
  }

  function setConfig(args) {
    root.note = root.t("saving")
    root.run(setProc, ["set"].concat(args))
  }

  function saveKey() {
    if (root.keyDraft === "" || keyProc.running) return
    root.note = root.t("savingKey")
    keyProc.command = root.helper.concat(["set", "--api-key", "-", "--lang", root.lang])
    keyProc.running = true
  }

  function toggleService() {
    root.note = root.t(root.serviceActive ? "restarting" : "starting")
    root.run(serviceProc, ["service", root.serviceActive ? "restart" : "start"])
  }

  // OpenRouter advertises ~300 models, so the list is only useful searchable;
  // fetching it as the panel opens means the search has something to search.
  function maybeFetchModels(force) {
    if (root.provider === "off" || modelsProc.running) return
    if (!force && root.modelsFailedFor === root.provider) return
    if (root.modelsFor === root.provider && root.modelOptions.length > 0) return
    if (force) root.modelsFailedFor = ""
    root.modelsFor = root.provider
    root.note = root.t("fetchingModels")
    root.run(modelsProc, ["models", "--provider", root.provider])
  }

  function keyPlaceholder() {
    if (root.keyStorage === "keyring") return root.t("keyStoredKeyring")
    if (root.keyStorage === "file") return root.t("keyStoredFile")
    if (root.keyStorage === "env") return root.t("keyStoredEnv")
    return root.llm.keyringAvailable === true ? root.t("keyNewKeyring")
                                              : root.t("keyNewFile")
  }

  function applyModels(text) {
    var names = String(text || "").split("\n")
    var out = []
    for (var i = 0; i < names.length; i++) {
      var name = names[i].replace(/^\s+|\s+$/g, "")
      if (name.length > 0) out.push({ value: name, label: name })
    }
    root.modelOptions = out
    root.note = out.length > 0 ? root.t("modelsFound").replace("{count}", String(out.length))
                               : root.t("modelsNone")
  }

  function stateText() {
    if (root.status.active === undefined) return root.t("stateLoading")
    if (!root.serviceActive) return root.t("stateDown")
    return root.link === "linked" ? root.t("stateLinked") : root.t("stateWaiting")
  }

  Process {
    id: setProc
    // stdout stays unread on purpose: `set` prints the saved path plus a
    // summary, which is longer than this note area and says nothing the panel
    // does not already show.
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var message = String(text || "").trim()
        // The configurator refuses impossible combinations (enable with no
        // provider, no model) here, in the panel's own language.
        if (message.length > 0) root.note = message.split("\n")[0]
      }
    }
    onExited: function (code) {
      if (code === 0) root.note = root.t("savedNote")
      else if (root.note === root.t("saving")) root.note = root.t("failed")
      root.refresh()
      root.maybeFetchModels()
    }
  }

  Process {
    id: keyProc
    stdinEnabled: true
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.note = String(text || "").trim().split("\n").pop()
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var message = String(text || "").trim()
        if (message.length > 0) root.note = message.split("\n")[0]
      }
    }
    onStarted: {
      // stdin, not argv: the key must not be readable in `ps`.
      if (root.keyDraft !== "") keyProc.write(root.keyDraft + "\n")
    }
    onExited: function (code) {
      root.keyDraft = ""
      if (code !== 0) root.note = root.t("failed")
      root.refresh()
    }
  }

  Process {
    id: modelsProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyModels(text)
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        var message = String(text || "").trim()
        if (message.length > 0) root.note = message.split("\n")[0]
      }
    }
    onExited: function (code) {
      if (code === 0) return
      // A failure is remembered for this provider: the panel opens often, and
      // repeating a rejected request every time helps nobody.
      root.modelsFailedFor = root.provider
      if (root.modelOptions.length === 0 && root.note === "")
        root.note = root.t("failed")
    }
  }

  Process {
    id: serviceProc
    onExited: function (code) {
      root.note = code === 0 ? "" : root.t("failed")
      root.refresh()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    contentWidth: panel.fittedContentWidth(Style.space(360))
    contentHeight: panel.fittedContentHeight(content.implicitHeight)

    Column {
      id: content
      width: parent.width
      spacing: Style.space(10)

      // ---- Header
      Item {
        width: parent.width
        implicitHeight: Math.max(headerText.implicitHeight, actionButton.height)

        Column {
          id: headerText
          anchors.left: parent.left
          anchors.right: actionButton.left
          anchors.rightMargin: Style.space(8)
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(2)

          Text {
            width: parent.width
            text: root.t("title")
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.subtitle
            font.bold: true
            elide: Text.ElideRight
          }

          Text {
            width: parent.width
            text: root.stateText()
            color: root.serviceActive ? root.dim : root.urgentColor
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
          }
        }

        PanelActionButton {
          id: actionButton
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          // Play when there is nothing to restart: the useful action follows
          // the state instead of asking the user to run a command themselves.
          iconText: root.serviceActive ? "\uf2f1" : "\uf04b"
          tooltipText: root.t(root.serviceActive ? "actionRestart" : "actionStart")
          foreground: root.foreground
          hoverColor: root.serviceActive ? root.foreground : root.urgentColor
          onClicked: root.toggleService()
        }
      }

      // ---- Live state
      Column {
        width: parent.width
        spacing: Style.space(2)

        Row {
          spacing: Style.space(6)

          Rectangle {
            width: Style.space(6)
            height: Style.space(6)
            radius: width / 2
            anchors.verticalCenter: parent.verticalCenter
            // Same three states as the bar icon: red = down, dim = waiting,
            // green = a device is connected.
            color: !root.serviceActive ? root.urgentColor
                 : root.link === "linked" ? root.connectedColor
                 : root.dim
          }

          Text {
            text: root.t(root.serviceActive ? "serviceRunning" : "serviceStopped")
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
          }
        }

        Text {
          width: parent.width
          visible: root.serviceActive && root.link !== "linked"
          text: root.t("waitingTip")
          color: root.dim
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
          wrapMode: Text.WordWrap
        }

        // The service being down is the one failure the panel can teach its way
        // out of: the two commands that fix it, verbatim.
        Text {
          width: parent.width
          visible: !root.serviceActive
          text: root.t("tipServiceDown")
          color: root.urgentColor
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
          wrapMode: Text.WrapAnywhere
        }

        Text {
          width: parent.width
          visible: root.lastText !== ""
          text: root.t("last") + ": " + root.lastText
          color: root.dim
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
          wrapMode: Text.WrapAnywhere
          maximumLineCount: 2
          elide: Text.ElideRight
        }

        Text {
          width: parent.width
          visible: root.lastError !== ""
          text: root.lastError
          color: root.urgentColor
          font.family: root.fontFamily
          font.pixelSize: Style.font.caption
          wrapMode: Text.WrapAnywhere
          maximumLineCount: 3
          elide: Text.ElideRight
        }
      }

      Rectangle {
        width: parent.width
        height: 1
        color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)
      }

      // ---- LLM cleanup
      Row {
        width: parent.width
        spacing: Style.space(8)

        Column {
          width: parent.width - enableSwitch.width - Style.space(8)
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(1)

          Text {
            width: parent.width
            text: root.t("llmTitle")
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
            font.bold: true
            elide: Text.ElideRight
          }

          Text {
            width: parent.width
            text: root.llm.enabled === true
              ? String(root.llm.providerLabel || "") + " · " + String(root.llm.model || "")
              : root.t("llmOff")
            color: root.dim
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            elide: Text.ElideRight
          }
        }

        ToggleSwitch {
          id: enableSwitch
          anchors.verticalCenter: parent.verticalCenter
          checked: root.switchOn
          foreground: root.foreground
          accent: Commons.Color.accent
          onToggled: root.setConfig([root.switchOn ? "--disable" : "--enable"])
        }
      }

      Dropdown {
        width: parent.width
        label: root.t("provider")
        value: root.provider
        options: root.providerOptions()
        foreground: root.foreground
        fontFamily: root.fontFamily
        onChanged: function (value) {
          // A provider switch also picks that provider's default model, so the
          // pair can never name a model belonging to the previous vendor — and
          // the fetched list goes with it.
          root.modelOptions = []
          root.modelsFor = ""
          root.modelsFailedFor = ""
          root.setConfig(["--provider", value])
        }
      }

      Row {
        width: parent.width
        spacing: Style.space(6)

        SearchableDropdown {
          width: parent.width - modelsButton.width - Style.space(6)
          label: root.t("model")
          value: String(root.llm.model || "")
          options: root.modelOptions.length > 0
            ? root.modelOptions
            : (root.llm.model ? [{ value: String(root.llm.model), label: String(root.llm.model) }] : [])
          triggerLabel: root.t("modelPick")
          placeholderText: root.t("modelSearch")
          emptyText: root.t("modelEmpty")
          foreground: root.foreground
          fontFamily: root.fontFamily
          onChanged: function (value) { root.setConfig(["--model", value]) }
        }

        PanelActionButton {
          id: modelsButton
          anchors.bottom: parent.bottom
          iconText: "\uf021"
          tooltipText: root.t("fetchModels")
          foreground: root.foreground
          onClicked: root.maybeFetchModels(true)
        }
      }

      Text {
        width: parent.width
        visible: root.provider !== "off" && root.modelOptions.length === 0
                 && String(root.llm.model || "") === ""
        text: root.t("modelHint")
        color: root.dim
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
      }

      TextField {
        width: parent.width
        visible: root.customProvider
        placeholderText: "https://host/v1"
        text: String(root.llm.baseUrl || "")
        foreground: root.foreground
        font.family: root.fontFamily
        onEditingFinished: if (text !== String(root.llm.baseUrl || "")) root.setConfig(["--base-url", text])
      }

      TextField {
        width: parent.width
        password: true
        placeholderText: root.keyPlaceholder()
        foreground: root.foreground
        font.family: root.fontFamily
        onTextEdited: root.keyDraft = text
        onAccepted: root.saveKey()
        onEditingFinished: root.saveKey()
      }

      // A plaintext file is the one case worth flagging in red: one re-entry
      // moves the key into the login keyring.
      Text {
        width: parent.width
        visible: root.keyStorage === "file"
        text: root.t("keyFileWarning")
        color: root.urgentColor
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
      }

      Text {
        width: parent.width
        text: root.note !== "" ? root.note : root.t("noteDefault")
        color: root.note !== "" ? Commons.Color.accent : root.dim
        font.family: root.fontFamily
        font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
        maximumLineCount: 2
        elide: Text.ElideRight
      }
    }
  }
}
