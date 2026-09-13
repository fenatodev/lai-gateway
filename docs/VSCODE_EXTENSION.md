# VS Code LAI Chat extension

Status: local unpacked extension MVP.

The extension registers the `@lai` chat participant in VS Code Chat and talks only to the loopback `lai-gateway` URL.

## Commands

- `@lai /health`: shows Gateway health.
- `@lai /workbench`: opens the browser Workbench.
- `@lai <prompt>`: creates a read-only `plan` run through the Gateway.

## Safety boundary

The VS Code chat participant does not expose write-capable LAI work runs. Code-changing work remains in the browser Workbench, where sandbox, review, patch-hash, and apply gates are already enforced.

## Local install

The development copy can be installed as an unpacked extension:

```bash
mkdir -p ~/.vscode/extensions
rm -rf ~/.vscode/extensions/fenatodev.lai-chat-0.1.0
cp -a vscode/lai-chat-extension ~/.vscode/extensions/fenatodev.lai-chat-0.1.0
```

Reload VS Code after copying the extension.
