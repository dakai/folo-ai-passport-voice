#!/usr/bin/env python3
"""Terminal configurator for the Linux voice forwarder's LLM cleanup.

Bare `voice_tui.py` opens the menu. The same file answers the machine-readable
subcommands the Omarchy bar widget calls (`status --json`, `set`, `models`,
`service`, `key`), so the plugin has no config logic of its own and both
surfaces change the same file the forwarder reads.

Every change is written immediately: no "save?" step to forget, and the
forwarder re-reads the `llm` block per utterance, so nothing needs a restart.

All output follows the locale (zh → Chinese, anything else → English); the
plugin passes `--lang` so the lines it echoes back into its panel match the
panel's own language.
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
import tempfile
import shlex

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llm_cleanup
import voice_config

BASE = os.path.dirname(os.path.abspath(__file__))
UNIT = voice_config.SERVICE_UNIT
SAMPLE = "呃 那个 我们 the the 明天下午 3 点发货吧 嗯 就是这样"

# Every string this program prints. `tr` formats the named placeholders, so a
# literal %s (the prompt marker) passes through untouched.
TEXT = {
    "zh": {
        "statusTitle": " AI Passport · 语音服务状态",
        "statusService": " 服务    {value}  ({unit})",
        "statusDevice": " 设备    {value}",
        "statusCleanup": " 整理    {value}",
        "statusKey": " Key     {value}{custom}",
        "statusLast": " 最近    {value}",
        "statusError": " 错误    {value}",
        "unknownServiceAction": "未知服务动作 '{action}'(start|stop|restart)",
        "systemctlFailed": "systemctl 失败: {error}",
        "serviceResult": "{unit}: {action} → {state}",
        "linkLinked": "已连接",
        "linkWaiting": "等待设备",
        "linkUnknown": "未知(服务未运行?)",
        "cleanupOff": "关闭 (只用本地识别)",
        "cleanupOn": "开启",
        "cleanupOffShort": "关闭",
        "customPromptSuffix": " · 自定义提示词",
        "keyWhereKeyring": "密钥环",
        "keyWhereFile": "明文文件(建议重新输入)",
        "keyWhereEnv": "环境变量",
        "keyWhereNone": "未设置",
        "saved": "已保存 {path}",
        "summary": "整理: {state} · provider={provider} · model={model} · key={key}",
        "keySavedShort": "已保存",
        "keyUnsetShort": "未设置",
        "keyStoredKeyring": "已存入登录密钥环",
        "keyStoredFile": "已写入配置文件(明文, 未装 secret-tool)",
        "keyStoredNone": "已清除",
        "nothingToChange": "没有要修改的项(见 --help)",
        "unknownProvider": "未知 provider '{provider}'; 可选: {options}",
        "enableDisableBoth": "--enable 与 --disable 只能选一个",
        "needProviderModel": "先选择 provider 和模型, 再开启整理",
        "modelsFailed": "获取模型列表失败: {error}",
        "modelsEmpty": "该端点没有返回模型",
        "testRaw": "原文    {text}",
        "testClean": "整理    {text}",
        "testEmpty": "(空)",
        "testFailed": "整理失败: {error}",
        "promptUnchanged": "未修改",
        "promptSaved": "提示词已保存",
        "promptReset": "已恢复内置提示词",
        "menuModel": " 2) 模型                {value}",
        "menuKey": " 3) API key             {value}",
        "menuToggle": " 4) 开启/关闭整理       {value}",
        "menuPrompt": " 5) 自定义提示词        {value}",
        "menuTest": " 6) 测试一句",
        "menuRestart": " 7) 重启服务",
        "menuLogs": " 8) 最近日志",
        "menuQuit": " q) 退出",
        "menuChoose": "选择",
        "on": "开",
        "off": "关",
        "custom": "自定义",
        "builtin": "内置",
        "chooseNumber": "选择编号(回车取消)",
        "chooseNumberOrName": "选择编号, 或直接输入模型名(回车取消)",
        "modelName": "模型名(默认 {default})",
        "fetchingModels": "正在从 {url} 获取模型列表…",
        "fetchFailed": "获取失败: {error}",
        "manualModel": "可以手动输入模型名",
        "needProvider": "先选 provider",
        "keyIntro": "Key 存入登录密钥环(secret-tool); 未装 libsecret 时才写入 "
                    "voice-config.json(权限 600), 都不写入 git",
        "keyCurrentSaved": "已保存, 回车保留, 输入 - 清除",
        "keyCurrentNone": "未设置",
        "keyPrompt": "新 API key",
        "keyCleared": "已清除 key",
        "keySavedMsg": "key 已保存",
        "toggleResult": "整理 → {state}",
        "promptIntro": "内置提示词会保留原话、去口头语、补标点。"
                       "自定义时用 %s 标记转写文本位置。",
        "editPromptAsk": "编辑自定义提示词? (y/N)",
        "testText": "测试文本",
        "journalFailed": "journalctl 失败: {error}",
        "failed": "失败: {error}",
        "providerSet": "provider → {value}",
        "modelSet": "model → {value}",
        "providerOff": "off",
    },
    "en": {
        "statusTitle": " AI Passport · voice service status",
        "statusService": " Service  {value}  ({unit})",
        "statusDevice": " Device   {value}",
        "statusCleanup": " Cleanup  {value}",
        "statusKey": " Key      {value}{custom}",
        "statusLast": " Last     {value}",
        "statusError": " Error    {value}",
        "unknownServiceAction": "unknown service action '{action}' (start|stop|restart)",
        "systemctlFailed": "systemctl failed: {error}",
        "serviceResult": "{unit}: {action} → {state}",
        "linkLinked": "connected",
        "linkWaiting": "waiting for the device",
        "linkUnknown": "unknown (service not running?)",
        "cleanupOff": "off (raw transcript only)",
        "cleanupOn": "on",
        "cleanupOffShort": "off",
        "customPromptSuffix": " · custom prompt",
        "keyWhereKeyring": "login keyring",
        "keyWhereFile": "plain-text file (re-enter to migrate)",
        "keyWhereEnv": "environment",
        "keyWhereNone": "not set",
        "saved": "saved {path}",
        "summary": "cleanup: {state} · provider={provider} · model={model} · key={key}",
        "keySavedShort": "saved",
        "keyUnsetShort": "not set",
        "keyStoredKeyring": "stored in the login keyring",
        "keyStoredFile": "written to the config file (plain text, secret-tool missing)",
        "keyStoredNone": "cleared",
        "nothingToChange": "nothing to change (see --help)",
        "unknownProvider": "unknown provider '{provider}'; choose: {options}",
        "enableDisableBoth": "use only one of --enable/--disable",
        "needProviderModel": "choose a provider and a model before enabling cleanup",
        "modelsFailed": "fetching models failed: {error}",
        "modelsEmpty": "the endpoint returned no models",
        "testRaw": "raw      {text}",
        "testClean": "cleaned  {text}",
        "testEmpty": "(empty)",
        "testFailed": "cleanup failed: {error}",
        "promptUnchanged": "unchanged",
        "promptSaved": "prompt saved",
        "promptReset": "restored the built-in prompt",
        "menuModel": " 2) model               {value}",
        "menuKey": " 3) API key             {value}",
        "menuToggle": " 4) cleanup on/off      {value}",
        "menuPrompt": " 5) custom prompt       {value}",
        "menuTest": " 6) try a sentence",
        "menuRestart": " 7) restart the service",
        "menuLogs": " 8) recent log",
        "menuQuit": " q) quit",
        "menuChoose": "choice",
        "on": "on",
        "off": "off",
        "custom": "custom",
        "builtin": "built-in",
        "chooseNumber": "number (empty cancels)",
        "chooseNumberOrName": "number, or type a model name (empty cancels)",
        "modelName": "model name (default {default})",
        "fetchingModels": "fetching models from {url}…",
        "fetchFailed": "fetch failed: {error}",
        "manualModel": "you can type a model name instead",
        "needProvider": "choose a provider first",
        "keyIntro": "the key goes to the login keyring (secret-tool); without "
                    "libsecret it is written to voice-config.json (mode 600). "
                    "Neither is in git",
        "keyCurrentSaved": "saved — Enter keeps it, type - to clear",
        "keyCurrentNone": "not set",
        "keyPrompt": "new API key",
        "keyCleared": "key cleared",
        "keySavedMsg": "key saved",
        "toggleResult": "cleanup → {state}",
        "promptIntro": "the built-in prompt keeps your words, drops fillers and "
                       "adds punctuation; use %s for the transcript position",
        "editPromptAsk": "edit the custom prompt? (y/N)",
        "testText": "test sentence",
        "journalFailed": "journalctl failed: {error}",
        "failed": "failed: {error}",
        "providerSet": "provider → {value}",
        "modelSet": "model → {value}",
        "providerOff": "off",
    },
    "es": {
        "statusTitle": " AI Passport · estado del servicio de voz",
        "statusService": " Servicio     {value}  ({unit})",
        "statusDevice": " Dispositivo  {value}",
        "statusCleanup": " Limpieza     {value}",
        "statusKey": " Clave        {value}{custom}",
        "statusLast": " Último       {value}",
        "statusError": " Error        {value}",
        "unknownServiceAction": "acción de servicio desconocida '{action}' (start|stop|restart)",
        "systemctlFailed": "systemctl falló: {error}",
        "serviceResult": "{unit}: {action} → {state}",
        "linkLinked": "conectado",
        "linkWaiting": "esperando el dispositivo",
        "linkUnknown": "desconocido (¿servicio detenido?)",
        "cleanupOff": "desactivada (solo transcripción local)",
        "cleanupOn": "activada",
        "cleanupOffShort": "desactivada",
        "customPromptSuffix": " · prompt personalizado",
        "keyWhereKeyring": "llavero de sesión",
        "keyWhereFile": "archivo en claro (vuelve a introducirla)",
        "keyWhereEnv": "variable de entorno",
        "keyWhereNone": "sin configurar",
        "saved": "guardado {path}",
        "summary": "limpieza: {state} · provider={provider} · model={model} · key={key}",
        "keySavedShort": "guardada",
        "keyUnsetShort": "sin configurar",
        "keyStoredKeyring": "guardada en el llavero de sesión",
        "keyStoredFile": "escrita en el archivo de configuración (texto claro, falta secret-tool)",
        "keyStoredNone": "borrada",
        "nothingToChange": "nada que cambiar (ver --help)",
        "unknownProvider": "provider desconocido '{provider}'; opciones: {options}",
        "enableDisableBoth": "usa solo uno de --enable/--disable",
        "needProviderModel": "elige provider y modelo antes de activar la limpieza",
        "modelsFailed": "no se pudo obtener la lista de modelos: {error}",
        "modelsEmpty": "el endpoint no devolvió modelos",
        "testRaw": "original  {text}",
        "testClean": "limpiado  {text}",
        "testEmpty": "(vacío)",
        "testFailed": "la limpieza falló: {error}",
        "promptUnchanged": "sin cambios",
        "promptSaved": "prompt guardado",
        "promptReset": "se restauró el prompt integrado",
        "menuModel": " 2) modelo              {value}",
        "menuKey": " 3) API key             {value}",
        "menuToggle": " 4) limpieza on/off     {value}",
        "menuPrompt": " 5) prompt propio       {value}",
        "menuTest": " 6) probar una frase",
        "menuRestart": " 7) reiniciar el servicio",
        "menuLogs": " 8) registro reciente",
        "menuQuit": " q) salir",
        "menuChoose": "opción",
        "on": "activada",
        "off": "desactivada",
        "custom": "personalizado",
        "builtin": "integrado",
        "chooseNumber": "número (vacío cancela)",
        "chooseNumberOrName": "número, o escribe el nombre del modelo (vacío cancela)",
        "modelName": "nombre del modelo (por defecto {default})",
        "fetchingModels": "obteniendo modelos de {url}…",
        "fetchFailed": "error al obtener: {error}",
        "manualModel": "también puedes escribir el nombre del modelo",
        "needProvider": "elige primero un provider",
        "keyIntro": "la clave va al llavero de sesión (secret-tool); sin libsecret se "
                    "escribe en voice-config.json (permisos 600). Ninguna de las dos "
                    "cosas está en git",
        "keyCurrentSaved": "guardada — Intro la mantiene, escribe - para borrarla",
        "keyCurrentNone": "sin configurar",
        "keyPrompt": "nueva API key",
        "keyCleared": "clave borrada",
        "keySavedMsg": "clave guardada",
        "toggleResult": "limpieza → {state}",
        "promptIntro": "el prompt integrado conserva tus palabras, quita muletillas y "
                       "añade puntuación; usa %s para la posición de la transcripción",
        "editPromptAsk": "¿editar el prompt personalizado? (y/N)",
        "testText": "frase de prueba",
        "journalFailed": "journalctl falló: {error}",
        "failed": "falló: {error}",
        "providerSet": "provider → {value}",
        "modelSet": "modelo → {value}",
        "providerOff": "off",
    },
    "ja": {
        "statusTitle": " AI Passport · 音声サービスの状態",
        "statusService": " サービス  {value}  ({unit})",
        "statusDevice": " デバイス  {value}",
        "statusCleanup": " 整形      {value}",
        "statusKey": " キー      {value}{custom}",
        "statusLast": " 最近      {value}",
        "statusError": " エラー    {value}",
        "unknownServiceAction": "不明なサービス操作 '{action}' (start|stop|restart)",
        "systemctlFailed": "systemctl が失敗しました: {error}",
        "serviceResult": "{unit}: {action} → {state}",
        "linkLinked": "接続済み",
        "linkWaiting": "デバイス待ち",
        "linkUnknown": "不明 (サービス停止中?)",
        "cleanupOff": "オフ (ローカル認識の原文のみ)",
        "cleanupOn": "オン",
        "cleanupOffShort": "オフ",
        "customPromptSuffix": " · カスタムプロンプト",
        "keyWhereKeyring": "ログインキーリング",
        "keyWhereFile": "平文ファイル (再入力して移行)",
        "keyWhereEnv": "環境変数",
        "keyWhereNone": "未設定",
        "saved": "保存しました {path}",
        "summary": "整形: {state} · provider={provider} · model={model} · key={key}",
        "keySavedShort": "保存済み",
        "keyUnsetShort": "未設定",
        "keyStoredKeyring": "ログインキーリングに保存しました",
        "keyStoredFile": "設定ファイルに書き込みました (平文、secret-tool なし)",
        "keyStoredNone": "削除しました",
        "nothingToChange": "変更する項目がありません (--help 参照)",
        "unknownProvider": "不明な provider '{provider}'; 選択肢: {options}",
        "enableDisableBoth": "--enable と --disable は同時に使えません",
        "needProviderModel": "整形を有効にする前に provider とモデルを選んでください",
        "modelsFailed": "モデル一覧の取得に失敗: {error}",
        "modelsEmpty": "エンドポイントがモデルを返しません",
        "testRaw": "原文    {text}",
        "testClean": "整形後  {text}",
        "testEmpty": "(空)",
        "testFailed": "整形に失敗: {error}",
        "promptUnchanged": "変更なし",
        "promptSaved": "プロンプトを保存しました",
        "promptReset": "内蔵プロンプトに戻しました",
        "menuModel": " 2) モデル              {value}",
        "menuKey": " 3) API key             {value}",
        "menuToggle": " 4) 整形オン/オフ       {value}",
        "menuPrompt": " 5) カスタムプロンプト  {value}",
        "menuTest": " 6) 1 文を試す",
        "menuRestart": " 7) サービスを再起動",
        "menuLogs": " 8) 直近のログ",
        "menuQuit": " q) 終了",
        "menuChoose": "選択",
        "on": "オン",
        "off": "オフ",
        "custom": "カスタム",
        "builtin": "内蔵",
        "chooseNumber": "番号 (空で取消)",
        "chooseNumberOrName": "番号、またはモデル名を入力 (空で取消)",
        "modelName": "モデル名 (既定 {default})",
        "fetchingModels": "{url} からモデル一覧を取得中…",
        "fetchFailed": "取得に失敗: {error}",
        "manualModel": "モデル名を直接入力できます",
        "needProvider": "先に provider を選んでください",
        "keyIntro": "キーはログインキーリング (secret-tool) に保存されます。libsecret が"
                    "無い場合のみ voice-config.json (権限 600) に書き込みます。"
                    "どちらも git には入りません",
        "keyCurrentSaved": "保存済み — Enter で維持、- で削除",
        "keyCurrentNone": "未設定",
        "keyPrompt": "新しい API key",
        "keyCleared": "キーを削除しました",
        "keySavedMsg": "キーを保存しました",
        "toggleResult": "整形 → {state}",
        "promptIntro": "内蔵プロンプトは言い回しを保ち、フィラーを除いて句読点を補います。"
                       "%s が原文の位置です",
        "editPromptAsk": "カスタムプロンプトを編集しますか? (y/N)",
        "testText": "テスト文",
        "journalFailed": "journalctl が失敗しました: {error}",
        "failed": "失敗: {error}",
        "providerSet": "provider → {value}",
        "modelSet": "モデル → {value}",
        "providerOff": "off",
    },
}

_LANG = "zh"


def set_lang(value="auto"):
    """Fix the output language for this run; returns the resolved code.

    The choice is pinned in voice_config too, so llm_cleanup's error text — the
    part the panel echoes back — is in the same language instead of following
    the shell's locale behind the user's back.
    """
    global _LANG
    _LANG = voice_config.resolve_lang(value)
    voice_config.set_lang_override(_LANG)
    return _LANG


def lang():
    return _LANG


def tr(name, **fields):
    # `name`, not `key`: callers pass a `key=` placeholder (the API key line),
    # which would collide with a parameter of that name.
    table = TEXT.get(_LANG) or TEXT["zh"]
    template = table.get(name)
    if template is None:
        template = TEXT["zh"].get(name, name)
    return template.format(**fields) if fields else template


# ---------------------------------------------------------------- service

def service_state(unit=UNIT):
    try:
        done = subprocess.run(["systemctl", "--user", "is-active", unit],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return (done.stdout or "").strip() or "unknown"


def service_action(action, unit=UNIT):
    if action not in ("start", "stop", "restart"):
        raise SystemExit(tr("unknownServiceAction", action=action))
    try:
        done = subprocess.run(["systemctl", "--user", action, unit], timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        print(tr("systemctlFailed", error=error), file=sys.stderr)
        return 1
    print(tr("serviceResult", unit=unit, action=action, state=service_state(unit)))
    return done.returncode


# ---------------------------------------------------------------- status

def resolve_lang(value="auto"):
    """Kept as a re-export: the plugin and llm_cleanup share one rule."""
    return voice_config.resolve_lang(value)


def status_object(cfg=None, lang="auto"):
    """Everything a UI needs about the forwarder, in one object."""
    cfg = cfg if cfg is not None else voice_config.load()
    lang = voice_config.resolve_lang(lang)
    llm = cfg["llm"]
    state = service_state()
    live = voice_config.read_status()
    provider = llm_cleanup.provider_of(llm)
    _key, key_storage = voice_config.resolve_api_key(llm)
    return {
        "unit": UNIT,
        "service": state,
        "active": state == "active",
        "link": str(live.get("link") or "unknown"),
        "updated": live.get("updated"),
        "lastText": str(live.get("lastText") or ""),
        "lastError": str(live.get("lastError") or ""),
        "forwarderDir": BASE,
        "config": voice_config.CONFIG_PATH,
        # The plugin's dropdowns are built from this, so the provider list has
        # exactly one definition: the one llm_cleanup requests against.
        "providers": [{"id": key, "label": llm_cleanup.label_for(key, lang)}
                      for key in [llm_cleanup.OFF] + list(llm_cleanup.PROVIDERS)],
        "llm": {
            "enabled": llm_cleanup.enabled(llm),
            "switchOn": bool(llm["enabled"]),
            "provider": provider,
            "providerLabel": llm_cleanup.label_for(provider, lang),
            "model": llm_cleanup.model_of(llm),
            "baseUrl": llm["base_url"],
            "hasKey": key_storage != "none",
            "keyStorage": key_storage,
            "keyringAvailable": bool(voice_config.secret_tool()),
            "custom": provider == "custom",
            "customPrompt": bool(llm_cleanup.prompt_override(llm)),
        },
    }


def link_text(link):
    return {"linked": tr("linkLinked"), "waiting": tr("linkWaiting")}.get(
        link, tr("linkUnknown"))


def print_status(obj):
    llm = obj["llm"]
    print("=" * 62)
    print(tr("statusTitle"))
    print("=" * 62)
    print(tr("statusService", value=obj["service"], unit=obj["unit"]))
    print(tr("statusDevice", value=link_text(obj["link"])))
    state = (f"{llm['providerLabel']} · {llm['model']}" if llm["enabled"]
             else tr("cleanupOff"))
    print(tr("statusCleanup", value=state))
    if llm["provider"] != "off":
        where = {"keyring": tr("keyWhereKeyring"), "file": tr("keyWhereFile"),
                 "env": tr("keyWhereEnv")}
        print(tr("statusKey", value=where.get(llm["keyStorage"], tr("keyWhereNone")),
                 custom=tr("customPromptSuffix") if llm["customPrompt"] else ""))
    if obj["lastText"]:
        print(tr("statusLast", value=one_line(obj["lastText"], 60)))
    if obj["lastError"]:
        print(tr("statusError", value=obj["lastError"]))
    print("=" * 62)


def one_line(text, limit):
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[:limit - 1] + "…"


# ---------------------------------------------------------------- writes

def apply_changes(cfg, args):
    """Apply `set` flags to a config dict; returns the changed key names."""
    changed = []
    llm = dict(cfg["llm"])
    if args.provider:
        if args.provider not in llm_cleanup.PROVIDERS and args.provider != llm_cleanup.OFF:
            raise SystemExit(tr("unknownProvider", provider=args.provider,
                                options=", ".join([llm_cleanup.OFF]
                                                  + list(llm_cleanup.PROVIDERS))))
        llm["provider"] = args.provider
        # Switching provider invalidates a model name from another vendor;
        # falling back to that provider's default keeps the pair consistent.
        if args.provider != llm_cleanup.OFF and not args.model:
            llm["model"] = llm_cleanup.PROVIDERS[args.provider][1]
        if args.provider == llm_cleanup.OFF:
            llm["model"] = ""
            llm["base_url"] = ""
        changed.append("provider")
    if args.model is not None:
        llm["model"] = args.model.strip()
        changed.append("model")
    if args.base_url is not None:
        llm["base_url"] = args.base_url.strip()
        changed.append("base_url")
    if args.api_key is not None:
        # "-" reads one line from stdin so the key never appears in argv,
        # which every local process can read.
        llm["api_key"] = (sys.stdin.readline() if args.api_key == "-"
                          else args.api_key).strip()
        changed.append("api_key")
    if args.clear_key:
        llm["api_key"] = ""
        changed.append("api_key")
    if args.timeout is not None:
        llm["timeout"] = args.timeout
        changed.append("timeout")
    if args.prompt_file is not None:
        if args.prompt_file == "":
            llm["prompt"] = ""
        else:
            with open(args.prompt_file, encoding="utf-8") as handle:
                llm["prompt"] = handle.read()
        changed.append("prompt")
    if args.enable and args.disable:
        raise SystemExit(tr("enableDisableBoth"))
    if args.enable:
        llm["enabled"] = True
        changed.append("enabled")
    if args.disable:
        llm["enabled"] = False
        changed.append("enabled")
    # Checked after every flag is applied, so `--provider X --model Y --enable`
    # in one call works while a half-configured enable is refused rather than
    # silently doing nothing.
    if llm["enabled"] and (llm_cleanup.provider_of(llm) == llm_cleanup.OFF
                           or not str(llm["model"]).strip()):
        raise SystemExit(tr("needProviderModel"))
    cfg["llm"] = llm
    return changed


def save_and_report(cfg, path=None):
    path = voice_config.save(cfg, path)
    llm = cfg["llm"]
    state = tr("cleanupOn") if llm_cleanup.enabled(llm) else tr("cleanupOffShort")
    print(tr("saved", path=path))
    print(tr("summary", state=state, provider=llm["provider"] or "off",
             model=llm["model"] or "-",
             key=tr("keySavedShort") if llm["api_key"] else tr("keyUnsetShort")))


# ---------------------------------------------------------------- commands

def cmd_status(args):
    obj = status_object(lang=args.lang)
    if args.json:
        print(json.dumps(obj, ensure_ascii=False))
    else:
        print_status(obj)
    return 0


def cmd_set(args):
    cfg = voice_config.load(args.config)
    changed = apply_changes(cfg, args)
    if not changed:
        print(tr("nothingToChange"))
        return 2
    storage = ""
    if "api_key" in changed:
        # Keyring first; the config file only when libsecret is missing. Either
        # way the plaintext copy is removed in the same save.
        storage = voice_config.store_api_key(cfg, cfg["llm"]["api_key"])
    save_and_report(cfg, args.config)
    if "api_key" in changed:
        print("Key: " + {"keyring": tr("keyStoredKeyring"),
                         "file": tr("keyStoredFile"),
                         "none": tr("keyStoredNone")}.get(storage, storage))
    return 0


def cmd_models(args):
    cfg = voice_config.load(args.config)
    llm = dict(cfg["llm"])
    if args.provider:
        # Only the endpoint matters for a listing; the configured model is
        # irrelevant here.
        llm["provider"] = args.provider
    if args.base_url is not None:
        llm["base_url"] = args.base_url
    try:
        names = llm_cleanup.fetch_models(llm)
    except llm_cleanup.CleanupError as error:
        print(tr("modelsFailed", error=error), file=sys.stderr)
        return 1
    if not names:
        print(tr("modelsEmpty"), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(names, ensure_ascii=False))
    else:
        print("\n".join(names))
    return 0


def cmd_test(args):
    cfg = voice_config.load(args.config)
    llm = dict(cfg["llm"])
    llm["enabled"] = True  # a test runs even while cleanup is switched off
    text = args.text or SAMPLE
    print(tr("testRaw", text=text))
    try:
        cleaned = llm_cleanup.clean(text, llm)
    except llm_cleanup.CleanupError as error:
        print(tr("testFailed", error=error), file=sys.stderr)
        return 1
    print(tr("testClean", text=cleaned or tr("testEmpty")))
    return 0


def cmd_service(args):
    if args.action == "status":
        print(service_state())
        return 0
    return service_action(args.action)


def cmd_prompt(args):
    cfg = voice_config.load(args.config)
    llm = cfg["llm"]
    if not args.edit:
        print(llm_cleanup.effective_prompt(llm))
        return 0
    edited = edit_prompt(llm_cleanup.prompt_override(llm))
    if edited is None:
        print(tr("promptUnchanged"))
        return 0
    llm["prompt"] = edited
    cfg["llm"] = llm
    voice_config.save(cfg, args.config)
    print(tr("promptSaved") if edited else tr("promptReset"))
    return 0


def edit_prompt(current):
    """Open $EDITOR on the prompt; None means the user backed out."""
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    handle, path = tempfile.mkstemp(prefix="aipv-prompt-", suffix=".txt")
    os.close(handle)
    try:
        with open(path, "w", encoding="utf-8") as out:
            out.write(current or "%s")  # %s marks where the transcript goes
        done = subprocess.run(shlex.split(editor) + [path])
        if done.returncode != 0:
            return None
        with open(path, encoding="utf-8") as handle:
            text = handle.read().strip()
        return "" if text == "%s" else text
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------- interactive

def default_model(provider):
    return llm_cleanup.PROVIDERS.get(provider, ("", "", False))[1]


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        return ""
    return answer or default


def menu_choose_provider(cfg):
    llm = cfg["llm"]
    ids = [llm_cleanup.OFF] + list(llm_cleanup.PROVIDERS)
    print(" provider:")
    for index, key in enumerate(ids, 1):
        mark = "*" if key == llm["provider"] else " "
        print(f"  {index}) {mark} {key:<10} {llm_cleanup.label_for(key, lang())}")
    choice = ask(tr("chooseNumber"))
    if not choice.isdigit() or not 1 <= int(choice) <= len(ids):
        return
    provider = ids[int(choice) - 1]
    previous = llm["provider"]
    llm["provider"] = provider
    if provider == llm_cleanup.OFF:
        llm["model"] = ""
        llm["base_url"] = ""
        llm["enabled"] = False
    elif not llm["model"] or llm["model"] == default_model(previous):
        # A model name belongs to the vendor that serves it; carrying the last
        # provider's default over would leave the pair pointing at a model that
        # does not exist here.
        llm["model"] = llm_cleanup.PROVIDERS[provider][1]
    cfg["llm"] = llm
    voice_config.save(cfg)
    print(tr("providerSet", value=provider))


def menu_choose_model(cfg):
    llm = cfg["llm"]
    provider = llm_cleanup.provider_of(llm)
    if provider == llm_cleanup.OFF:
        print(tr("needProvider"))
        return
    print(tr("fetchingModels", url=llm_cleanup.base_url(llm)))
    names = []
    try:
        names = llm_cleanup.fetch_models(llm)
    except llm_cleanup.CleanupError as error:
        print(tr("fetchFailed", error=error))
        print(tr("manualModel"))
    if names:
        for index, name in enumerate(names[:60], 1):
            mark = "*" if name == llm["model"] else " "
            print(f"  {index}) {mark} {name}")
        choice = ask(tr("chooseNumberOrName"))
    else:
        choice = ask(tr("modelName",
                        default=llm["model"] or llm_cleanup.PROVIDERS[provider][1]))
    if not choice:
        return
    if choice.isdigit() and names and 1 <= int(choice) <= min(len(names), 60):
        model = names[int(choice) - 1]
    elif choice.isdigit() and not names:
        return
    else:
        model = choice
    llm["model"] = model
    cfg["llm"] = llm
    voice_config.save(cfg)
    print(tr("modelSet", value=model))


def menu_api_key(cfg):
    llm = cfg["llm"]
    print(tr("keyIntro"))
    storage = voice_config.resolve_api_key(llm)[1]
    print(tr("menuKey", value={"keyring": tr("keyWhereKeyring"),
                               "file": tr("keyWhereFile"),
                               "env": tr("keyWhereEnv")}.get(storage, tr("keyCurrentNone"))))
    try:
        key = getpass.getpass(tr("keyPrompt") + ": ").strip()
    except EOFError:
        return
    if not key:
        return
    # Same storage rule as `set --api-key`: keyring when it exists, and the
    # plaintext copy in the config is dropped either way.
    cfg["llm"]["api_key"] = "" if key == "-" else key
    voice_config.store_api_key(cfg, cfg["llm"]["api_key"])
    voice_config.save(cfg)
    print(tr("keyCleared") if key == "-" else tr("keySavedMsg"))


def menu_toggle(cfg):
    llm = cfg["llm"]
    if not llm["enabled"]:
        if (llm_cleanup.provider_of(llm) == llm_cleanup.OFF
                or not str(llm["model"]).strip()):
            print(tr("needProviderModel"))
            return
        llm["enabled"] = True
    else:
        llm["enabled"] = False
    cfg["llm"] = llm
    voice_config.save(cfg)
    print(tr("toggleResult", state=tr("on") if llm_cleanup.enabled(llm) else tr("off")))


def menu_prompt(cfg):
    llm = cfg["llm"]
    print(tr("promptIntro"))
    if not ask(tr("editPromptAsk")).lower().startswith("y"):
        return
    edited = edit_prompt(llm_cleanup.prompt_override(llm))
    if edited is None:
        print(tr("promptUnchanged"))
        return
    llm["prompt"] = edited
    cfg["llm"] = llm
    voice_config.save(cfg)
    print(tr("promptSaved") if edited else tr("promptReset"))


def menu_test(cfg):
    llm = dict(cfg["llm"])
    llm["enabled"] = True
    text = ask(tr("testText"), SAMPLE)
    print(tr("testRaw", text=text))
    try:
        print(tr("testClean", text=llm_cleanup.clean(text, llm) or tr("testEmpty")))
    except llm_cleanup.CleanupError as error:
        print(tr("testFailed", error=error))


def menu_logs():
    try:
        subprocess.run(["journalctl", "--user", "-u", UNIT, "-n", "20",
                        "--no-pager", "--output=cat"])
    except (OSError, subprocess.SubprocessError) as error:
        print(tr("journalFailed", error=error))


def interactive():
    while True:
        cfg = voice_config.load()
        print()
        print_status(status_object(cfg, lang=lang()))
        llm = cfg["llm"]
        provider = llm_cleanup.provider_of(llm)
        print(" 1) provider            "
              + (tr("providerOff") if provider == llm_cleanup.OFF
                 else llm_cleanup.label_for(provider, lang())))
        print(tr("menuModel", value=llm_cleanup.model_of(llm) or "-"))
        storage = voice_config.resolve_api_key(llm)[1]
        print(tr("menuKey", value={"keyring": tr("keyWhereKeyring"),
                                   "file": tr("keyWhereFile"),
                                   "env": tr("keyWhereEnv")}.get(storage, tr("keyWhereNone"))))
        print(tr("menuToggle", value=tr("on") if llm_cleanup.enabled(llm) else tr("off")))
        print(tr("menuPrompt", value=tr("custom") if llm["prompt"] else tr("builtin")))
        print(tr("menuTest"))
        print(tr("menuRestart"))
        print(tr("menuLogs"))
        print(tr("menuQuit"))
        choice = ask(tr("menuChoose"))
        try:
            if choice == "1":
                menu_choose_provider(cfg)
            elif choice == "2":
                menu_choose_model(cfg)
            elif choice == "3":
                menu_api_key(cfg)
            elif choice == "4":
                menu_toggle(cfg)
            elif choice == "5":
                menu_prompt(cfg)
            elif choice == "6":
                menu_test(cfg)
            elif choice == "7":
                service_action("restart")
            elif choice == "8":
                menu_logs()
            elif choice in ("q", "Q"):
                return 0
        except llm_cleanup.CleanupError as error:
            print(tr("failed", error=error), file=sys.stderr)
        except KeyboardInterrupt:
            return 0


# ---------------------------------------------------------------- cli

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=voice_config.CONFIG_PATH,
                        help="配置文件路径 / config file (默认 linux/voice-config.json)")
    common.add_argument("--lang", default="auto",
                        choices=["auto"] + list(voice_config.LANGUAGES),
                        help="输出语言 / output language: auto follows the locale")
    # Subcommands repeat the flags so `status --config X` works, but with
    # SUPPRESS: a subparser default would otherwise overwrite a flag given
    # before the subcommand name.
    sub_common = argparse.ArgumentParser(add_help=False)
    sub_common.add_argument("--config", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub_common.add_argument("--lang", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(
        parents=[common],
        description="AI Passport 语音服务配置器 / voice service configurator: "
                    "选择 LLM provider 与模型, 让识别结果像 Typeless 一样去掉口头语并"
                    "补标点。不带子命令进入交互菜单。")
    subs = parser.add_subparsers(dest="command")

    status = subs.add_parser("status", parents=[sub_common],
                             help="服务/链路/整理状态 · service/link/cleanup state")
    status.add_argument("--json", action="store_true", help="供插件读取的 JSON · JSON for the plugin")
    status.set_defaults(func=cmd_status)

    setter = subs.add_parser("set", parents=[sub_common],
                             help="修改 provider/模型/key/开关 · change provider/model/key/switch")
    setter.add_argument("--provider")
    setter.add_argument("--model", nargs="?", const="")
    setter.add_argument("--base-url", dest="base_url")
    setter.add_argument("--api-key", dest="api_key",
                        help="API key; '-' reads it from stdin")
    setter.add_argument("--clear-key", action="store_true")
    setter.add_argument("--timeout", type=float)
    setter.add_argument("--prompt-file", help="自定义提示词文件, 空字符串恢复内置 · "
                                              "custom prompt file, empty restores the built-in one")
    setter.add_argument("--enable", action="store_true")
    setter.add_argument("--disable", action="store_true")
    setter.set_defaults(func=cmd_set)

    models = subs.add_parser("models", parents=[sub_common],
                             help="列出端点可用模型 · list the endpoint's models")
    models.add_argument("--provider")
    models.add_argument("--base-url", dest="base_url")
    models.add_argument("--json", action="store_true")
    models.set_defaults(func=cmd_models)

    test = subs.add_parser("test", parents=[sub_common],
                           help="对一句话试跑整理 · run cleanup on one sentence")
    test.add_argument("text", nargs="?")
    test.set_defaults(func=cmd_test)

    service = subs.add_parser("service", parents=[sub_common],
                              help="启动/停止/重启服务 · start/stop/restart the service")
    service.add_argument("action", choices=["start", "stop", "restart", "status"])
    service.set_defaults(func=cmd_service)

    prompt = subs.add_parser("prompt", parents=[sub_common],
                             help="查看或编辑自定义提示词 · show or edit the custom prompt")
    prompt.add_argument("--edit", action="store_true")
    prompt.set_defaults(func=cmd_prompt)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    set_lang(getattr(args, "lang", "auto"))
    if not getattr(args, "command", None):
        try:
            return interactive()
        except KeyboardInterrupt:
            print()
            return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
