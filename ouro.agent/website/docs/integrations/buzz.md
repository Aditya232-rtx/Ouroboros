---
sidebar_position: 4
title: "Buzz Integration"
description: "All three ways to connect Ouro to Buzz — Block's Nostr-based human+agent workspace"
---

# Buzz Integration

[Buzz](https://github.com/block/buzz) is Block's open-source, self-hostable workspace where humans and AI agents share the same channels. It is built on Nostr: every message is a signed event on a relay you own, and every participant — human or agent — is a keypair.

Ouro integrates with Buzz three ways. Pick by where Ouro runs and what you want it to do:

| | ① Desktop runtime | ② Relay bridge (ACP) | ③ Native gateway platform |
|---|---|---|---|
| **What it is** | Buzz Desktop spawns Ouro locally as a managed harness | Buzz's `buzz-acp` bridges a channel to `ouro acp` over stdio | Ouro' gateway joins Buzz as a first-class messaging platform |
| **Ouro runs** | On your desktop, launched by Buzz | On a server, launched by `buzz-acp` | In your own gateway, alongside Telegram/Discord/etc. |
| **Best for** | Trying Ouro inside Buzz Desktop with zero config | A hosted agent identity when Buzz owns the transport | Full Ouro: memory, skills, approvals, cron, sessions |
| **Inbound** | ACP stdio | ACP stdio (via relay WebSocket) | NIP-42-authenticated Nostr WebSocket (poll fallback) |
| **Setup** | Automatic discovery | `buzz-acp` env vars | `ouro gateway setup` → Buzz |

## ① Buzz Desktop managed runtime

Buzz Desktop ships Ouro as a preset runtime. With Ouro installed the normal way, open **Settings → Runtimes** and Ouro appears automatically — discovery resolves the `ouro-acp` launcher on your login-shell PATH, which the installer writes to `~/.local/bin` (and `ouro update` self-heals on older installs).

Full setup, troubleshooting, and the security posture (Buzz auto-approves tool permissions — keep agents owner-only): **[ACP Host Integration → Buzz Desktop](/user-guide/features/acp#buzz-desktop)**

## ② Relay bridge (buzz-acp + ACP)

For a hosted Ouro identity that joins Buzz *channels* while Buzz's own harness owns the transport:

```text
Buzz relay <-- WebSocket --> buzz-acp <-- ACP over stdio --> Ouro
```

The spawned Ouro uses the same config, credentials, memory, and skills as `hermes` on that host. Key minting, channel discovery, owner-only telemetry (`BUZZ_ACP_RELAY_OBSERVER`), and headless-permission guidance: **[ACP Host Integration → Buzz channels (relay bridge)](/user-guide/features/acp#buzz-channels-relay-bridge)**

## ③ Native gateway platform (recommended for full Ouro)

The bundled `buzz` platform plugin makes Buzz a normal Ouro messaging platform — channels, DMs, mention gating, threaded replies, reactions, images, and cron delivery (`deliver=buzz`), with Ouro' own approvals, memory, and session management intact. Inbound arrives over a persistent NIP-42-authenticated Nostr WebSocket (dependency-free BIP-340 signing) with automatic fallback to CLI polling; outbound goes through the `buzz` CLI.

```bash
ouro gateway setup   # pick Buzz
```

Full configuration reference (env vars, config.yaml, transport modes, access control): **[Messaging → Buzz](/user-guide/messaging/buzz)**

## Which one should I use?

- **Just exploring, Buzz Desktop user** → ① works out of the box.
- **Running a community relay and want an agent identity managed by Buzz** → ②.
- **You already run Ouro as your agent and want Buzz as another channel** → ③. This is the deepest integration and the one that keeps every Ouro feature.

①/② and ③ use different identities and transports; run ③ with its own dedicated Nostr keypair. The adapter takes a scoped lock on the relay+pubkey pair, so two Ouro profiles cannot accidentally drive one Buzz identity.

## Credits

The Buzz integration was built with the community: @SHL0MS (PATH launcher + Desktop security audit), @NYTEMODEONLY (relay-bridge docs), @rob-coco (platform adapter), @ScaleLeanChris (Nostr WebSocket transport + NIP-42/BIP-340 signing), and @jethac (multi-agent verification).
