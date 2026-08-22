# Ouro CLI Reference

Live sources when anything looks stale: `ouro --help`, `ouro <command> --help`,
https://ouro.dev/docs/reference/cli-commands

### Global Flags

```
ouro [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
ouro chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
ouro setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
ouro model                Interactive model/provider picker
ouro fallback [add|remove|list]  Fallback provider chain
ouro config [show|edit|get|set|unset|path|env-path|check|migrate]
ouro login / logout       OAuth sign-in / clear stored auth
ouro doctor [--fix]       Check dependencies and config
ouro status [--all]       Component status
```

### Tools & Skills

```
ouro tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

ouro skills list|browse|search QUERY|inspect ID
ouro skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
ouro skills config        Enable/disable skills per platform
ouro skills check|update|uninstall|publish PATH
ouro skills tap add REPO  Add a GitHub repo as a skill source
ouro bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
ouro mcp add NAME (--url or --command) | remove | list | test NAME
ouro mcp catalog | install NAME     Curated catalog install
ouro mcp configure NAME             Toggle tool selection
ouro mcp serve                      Run Ouro as an MCP server
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
ouro gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `ouro photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://ouro.dev/docs/user-guide/messaging/

### Sessions

```
ouro sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
ouro cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
ouro webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
ouro profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
ouro profile rename A B | alias NAME | export NAME | import FILE
```

### Credentials & Pools

```
ouro auth                 Interactive credential manager
ouro auth add [PROVIDER]  Add OAuth or API-key credential (nous, openai-codex, qwen-oauth, …)
ouro auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
ouro desktop / gui        Native desktop app
ouro dashboard            Web admin panel + embedded chat (--stop / --status)
ouro proxy                OpenAI-compatible local proxy backed by an OAuth provider
ouro portal               Quick setup / sign in via Nous Portal
ouro kanban <verb>        Multi-agent work-queue board
ouro project              Named multi-folder workspaces
ouro skin list|use|set    Switch/tweak skins (see references/themes.md)
ouro pets <verb>          Pet mascots (see references/petdex.md)
ouro memory setup|status|off|reset   Memory provider
ouro secrets bitwarden|onepassword   External secret stores
ouro moa                  Mixture-of-Agents slots
ouro hooks / security / backup / import / checkpoints / console
ouro logs [-f] [errors]   View agent/error logs
ouro send                 One-off message through a gateway platform
ouro pairing / plugins / insights / journey / computer-use
ouro acp                  ACP server (IDE integration)
ouro completion bash|zsh|fish
ouro update / uninstall / claw migrate
```

Plugin- and provider-supplied subcommands (e.g. `ouro photon setup`) only appear once their plugin is installed/active.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `ouro config edit` · [Configuration docs](https://ouro.dev/docs/user-guide/configuration) |
| Tools / toolsets | `ouro tools list` · [Tools reference](https://ouro.dev/docs/reference/tools-reference) |
| Skills catalog | `ouro skills browse` · [Skills catalog](https://ouro.dev/docs/reference/skills-catalog) |
| Provider setup | `ouro model` · [Providers guide](https://ouro.dev/docs/integrations/providers) |
| Env variables | `ouro config env-path` · [Env vars reference](https://ouro.dev/docs/reference/environment-variables) |
| Gateway logs | `~/.ouro/logs/gateway.log` (or `ouro logs`) |
| Sessions | `ouro sessions browse` (reads state.db) |
