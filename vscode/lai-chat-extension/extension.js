const vscode = require("vscode");
const http = require("http");

function configuredGatewayUrl() {
  const raw = vscode.workspace.getConfiguration("lai").get("gatewayUrl") || "http://127.0.0.1:8787";
  try {
    const url = new URL(String(raw));
    if (!["127.0.0.1", "localhost", "[::1]", "::1"].includes(url.hostname)) {
      throw new Error("O LAI no VS Code só fala com um Gateway em loopback.");
    }
    return url.origin;
  } catch (err) {
    throw new Error(`lai.gatewayUrl inválido: ${err.message}`);
  }
}

function requestJson(method, path, body = null) {
  return new Promise((resolve, reject) => {
    let origin;
    try {
      origin = configuredGatewayUrl();
    } catch (err) {
      reject(err);
      return;
    }
    const target = new URL(path, origin);
    const payload = body ? Buffer.from(JSON.stringify(body), "utf8") : null;
    const headers = { Accept: "application/json" };
    if (payload) {
      headers["Content-Type"] = "application/json; charset=utf-8";
      headers["Content-Length"] = String(payload.length);
    }
    const req = http.request(target, { method, headers, timeout: 15000 }, (res) => {
      const chunks = [];
      let size = 0;
      res.on("data", (chunk) => {
        size += chunk.length;
        if (size <= 256 * 1024) chunks.push(chunk);
      });
      res.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        let json = {};
        try {
          json = text ? JSON.parse(text) : {};
        } catch (_err) {
          json = { error: "json_invalido", body: text.slice(0, 2000) };
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`Gateway HTTP ${res.statusCode}: ${JSON.stringify(json).slice(0, 2000)}`));
          return;
        }
        resolve(json);
      });
    });
    req.on("timeout", () => req.destroy(new Error("A requisição ao Gateway expirou.")));
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function compactHealthMarkdown(payload) {
  const checks = payload.checks || {};
  const mcp = payload.mcp || {};
  return [
    `**Saúde do LAI:** ${payload.overall || "desconhecida"}`,
    "",
    `- doctor: ${checks.doctor || "desconhecido"}`,
    `- modelo: ${checks.gateway_model_probe || "desconhecido"}`,
    `- runs do modelo: ${checks.model_runs || "desconhecido"}`,
    `- mobile: ${checks.mobile || "desconhecido"}`,
    `- telegram: ${checks.telegram || "desconhecido"}`,
    `- mcp: ${checks.mcp_broker || "desconhecido"}, servidores=${mcp.server_count || 0}, execução=${Boolean(mcp.execution_enabled)}`,
    "",
    "Use `@lai /workbench` para Work/Review/Apply com sandbox e gates explícitos."
  ].join("\n");
}

async function openWorkbench() {
  const uri = vscode.Uri.parse(configuredGatewayUrl() + "/");
  await vscode.env.openExternal(uri);
}

function workspacePath(workspace) {
  const candidates = [
    workspace.client_path_authority,
    workspace.path_authority,
    workspace.source_checkout_path,
    workspace.repository_path,
  ].filter((value) => typeof value === "string" && value.startsWith("/"));
  return candidates[0] || "";
}

async function gatewayWorkspacePicks() {
  try {
    const payload = await requestJson("GET", "/v1/local-chat/workspaces");
    const workspaces = Array.isArray(payload.workspaces) ? payload.workspaces : [];
    return workspaces
      .map((workspace) => {
        const path = workspacePath(workspace);
        if (!path) return null;
        return {
          label: workspace.display_name || workspace.repository_name || "workspace LAI",
          description: workspace.repository_name || "workspace do Harness",
          detail: "Projeto conhecido pelo LAI Gateway",
          uri: vscode.Uri.file(path),
          action: "open-uri",
        };
      })
      .filter(Boolean);
  } catch (_err) {
    return [];
  }
}

async function openFolderOrRepository() {
  const current = vscode.workspace.workspaceFolders || [];
  const gatewayPicks = await gatewayWorkspacePicks();
  const picks = [
    ...gatewayPicks,
    { label: "Escolher outra pasta/repositório", description: "Abre o seletor de pastas do VS Code", action: "pick" },
    ...current.map((folder) => ({
      label: folder.name,
      description: "Pasta já aberta neste VS Code",
      detail: "Workspace atual",
      folder,
      action: "open",
    })),
  ];
  const selected = await vscode.window.showQuickPick(picks, {
    title: "LAI: abrir pasta ou repositório",
    placeHolder: "Escolha um projeto para abrir ou focar na barra lateral do VS Code",
  });
  if (!selected) return;
  if (selected.action === "pick") {
    const folder = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      openLabel: "Abrir repositório",
      title: "Escolha a pasta/repositório do projeto",
    });
    if (folder && folder[0]) {
      await vscode.commands.executeCommand("vscode.openFolder", folder[0], false);
    }
    return;
  }
  if (selected.action === "open-uri" && selected.uri) {
    await vscode.commands.executeCommand("vscode.openFolder", selected.uri, false);
    return;
  }
  if (selected.folder) {
    await vscode.commands.executeCommand("workbench.files.action.focusFilesExplorer");
    await vscode.window.showInformationMessage(`Projeto ativo no VS Code: ${selected.folder.name}`);
  }
}

async function showHealth() {
  const payload = await requestJson("GET", "/v1/gateway/health-report");
  await vscode.window.showInformationMessage(`Saúde do LAI: ${payload.overall || "desconhecida"}`);
  return payload;
}

async function handleChatRequest(request, _context, stream, _token) {
  const command = request.command || "";
  const prompt = (request.prompt || "").trim();
  if (command === "workbench") {
    await openWorkbench();
    stream.markdown("Workbench local do LAI aberto. Use ele para Trabalhar, Revisar e Aplicar.");
    return {};
  }
  if (command === "pasta") {
    await openFolderOrRepository();
    stream.markdown("Abrindo seletor de pasta/repositório do VS Code.");
    return {};
  }
  if (command === "health" || !prompt) {
    const payload = await requestJson("GET", "/v1/gateway/health-report");
    stream.markdown(compactHealthMarkdown(payload));
    return {};
  }
  if (command === "plan") {
    stream.progress("Criando run read-only de plano no LAI...");
    const task = prompt.slice(0, 12000);
    const payload = await requestJson("POST", "/v1/harness/runs", { mode: "plan", task });
    const run = payload.run || payload;
    const runId = run.control_run_id || run.run_id || "desconhecido";
    const status = run.status || "enfileirado";
    stream.markdown([
      `Run **read-only** de plano enfileirado: \`${runId}\`.`,
      "",
      `Status: ${status}`,
      "",
      "Para alterar código, use `@lai /workbench`; o Workbench mantém alterações em sandbox e exige revisão antes de aplicar."
    ].join("\n"));
    return { metadata: { runId, mode: "plan" } };
  }
  stream.progress("Conversa direta no LAI local...");
  const payload = await requestJson("POST", "/v1/gateway/chat", {
    message: prompt.slice(0, 12000),
    max_tokens: 768,
    timeout_seconds: 60,
  });
  if (payload.overall === "ready" && payload.message) {
    stream.markdown(payload.message);
    return { metadata: { mode: "conversation" } };
  }
  stream.markdown([
    "Conversa direta indisponível no modelo local configurado.",
    "",
    "Use `@lai /health` para diagnóstico ou `@lai /plan <pedido>` para criar um plano read-only no Harness."
  ].join("\n"));
  return { metadata: { mode: "conversation", status: payload.overall || "blocked" } };
}

class LaiProjectsProvider {
  constructor() {
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
  }

  refresh() {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(item) {
    return item;
  }

  async getChildren() {
    const items = [];
    items.push(new CommandItem("Abrir Workbench", "lai.openWorkbench", "Abre a UI local do LAI no navegador", "browser"));
    items.push(new CommandItem("Abrir pasta/repositório", "lai.openFolder", "Escolhe ou foca um projeto no VS Code", "repo"));
    const folders = vscode.workspace.workspaceFolders || [];
    for (const folder of folders) {
      const item = new vscode.TreeItem(folder.name, vscode.TreeItemCollapsibleState.None);
      item.description = "workspace aberto";
      item.tooltip = "Pasta já aberta no VS Code";
      item.resourceUri = folder.uri;
      item.iconPath = new vscode.ThemeIcon("folder");
      items.push(item);
    }
    const gatewayPicks = await gatewayWorkspacePicks();
    for (const pick of gatewayPicks) {
      const item = new vscode.TreeItem(pick.label, vscode.TreeItemCollapsibleState.None);
      item.description = "conhecido pelo LAI";
      item.tooltip = pick.description;
      item.resourceUri = pick.uri;
      item.iconPath = new vscode.ThemeIcon("repo");
      item.command = { command: "vscode.openFolder", title: "Abrir", arguments: [pick.uri, false] };
      items.push(item);
    }
    if (!folders.length && !gatewayPicks.length) {
      const item = new vscode.TreeItem("Nenhum repositório aberto", vscode.TreeItemCollapsibleState.None);
      item.description = "use Abrir pasta/repositório";
      item.iconPath = new vscode.ThemeIcon("info");
      items.push(item);
    }
    return items;
  }
}

class CommandItem extends vscode.TreeItem {
  constructor(label, command, tooltip, icon) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.tooltip = tooltip;
    this.iconPath = new vscode.ThemeIcon(icon);
    this.command = { command, title: label };
  }
}

function activate(context) {
  const provider = new LaiProjectsProvider();
  context.subscriptions.push(vscode.window.registerTreeDataProvider("lai.projects", provider));
  context.subscriptions.push(vscode.commands.registerCommand("lai.openWorkbench", openWorkbench));
  context.subscriptions.push(vscode.commands.registerCommand("lai.openFolder", openFolderOrRepository));
  context.subscriptions.push(vscode.commands.registerCommand("lai.health", showHealth));
  context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders(() => provider.refresh()));
  context.subscriptions.push(vscode.window.registerUriHandler({
    handleUri(uri) {
      if (uri.path.includes("open-folder")) return openFolderOrRepository();
      if (uri.path.includes("open-workbench")) return openWorkbench();
      return openWorkbench();
    },
  }));
  if (vscode.chat && typeof vscode.chat.createChatParticipant === "function") {
    const participant = vscode.chat.createChatParticipant("lai.assistant", async (request, chatContext, stream, token) => {
      try {
        return await handleChatRequest(request, chatContext, stream, token);
      } catch (err) {
        stream.markdown(`LAI indisponível: ${err.message || String(err)}\n\nInicie a stack com \`lai-gateway stack-start\`.`);
        return {};
      }
    });
    context.subscriptions.push(participant);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
