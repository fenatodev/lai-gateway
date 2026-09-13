const vscode = require("vscode");
const http = require("http");

function configuredGatewayUrl() {
  const raw = vscode.workspace.getConfiguration("lai").get("gatewayUrl") || "http://127.0.0.1:8787";
  try {
    const url = new URL(String(raw));
    if (!["127.0.0.1", "localhost", "[::1]", "::1"].includes(url.hostname)) {
      throw new Error("LAI VS Code chat only talks to a loopback gateway URL.");
    }
    return url.origin;
  } catch (err) {
    throw new Error(`Invalid lai.gatewayUrl: ${err.message}`);
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
          json = { error: "invalid_json", body: text.slice(0, 2000) };
        }
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`Gateway HTTP ${res.statusCode}: ${JSON.stringify(json).slice(0, 2000)}`));
          return;
        }
        resolve(json);
      });
    });
    req.on("timeout", () => req.destroy(new Error("Gateway request timed out.")));
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function compactHealthMarkdown(payload) {
  const checks = payload.checks || {};
  const mcp = payload.mcp || {};
  return [
    `**LAI health:** ${payload.overall || "unknown"}`,
    "",
    `- doctor: ${checks.doctor || "unknown"}`,
    `- model: ${checks.gateway_model_probe || "unknown"}`,
    `- model runs: ${checks.model_runs || "unknown"}`,
    `- mobile: ${checks.mobile || "unknown"}`,
    `- telegram: ${checks.telegram || "unknown"}`,
    `- mcp: ${checks.mcp_broker || "unknown"}, servers=${mcp.server_count || 0}, execution=${Boolean(mcp.execution_enabled)}`,
    "",
    "Use `@lai /workbench` for sandboxed Work/Review/Apply."
  ].join("\n");
}

async function openWorkbench() {
  const uri = vscode.Uri.parse(configuredGatewayUrl() + "/");
  await vscode.env.openExternal(uri);
}

async function showHealth() {
  const payload = await requestJson("GET", "/v1/gateway/health-report");
  await vscode.window.showInformationMessage(`LAI health: ${payload.overall || "unknown"}`);
  return payload;
}

async function handleChatRequest(request, _context, stream, _token) {
  const command = request.command || "";
  const prompt = (request.prompt || "").trim();
  if (command === "workbench") {
    await openWorkbench();
    stream.markdown("Opened the local LAI Workbench. Use it for Work, Review, and Apply.");
    return {};
  }
  if (command === "health" || !prompt) {
    const payload = await requestJson("GET", "/v1/gateway/health-report");
    stream.markdown(compactHealthMarkdown(payload));
    return {};
  }
  stream.progress("Creating a read-only LAI plan run...");
  const task = prompt.slice(0, 12000);
  const payload = await requestJson("POST", "/v1/harness/runs", { mode: "plan", task });
  const run = payload.run || payload;
  const runId = run.control_run_id || run.run_id || "unknown";
  const status = run.status || "queued";
  stream.markdown([
    `Queued **read-only** LAI plan run: \`${runId}\`.`,
    "",
    `Status: ${status}`,
    "",
    "For code changes, use `@lai /workbench`; the browser Workbench keeps edits sandboxed and requires review before apply."
  ].join("\n"));
  return { metadata: { runId, mode: "plan" } };
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand("lai.openWorkbench", openWorkbench));
  context.subscriptions.push(vscode.commands.registerCommand("lai.health", showHealth));
  if (vscode.chat && typeof vscode.chat.createChatParticipant === "function") {
    const participant = vscode.chat.createChatParticipant("lai.assistant", async (request, chatContext, stream, token) => {
      try {
        return await handleChatRequest(request, chatContext, stream, token);
      } catch (err) {
        stream.markdown(`LAI unavailable: ${err.message || String(err)}\n\nStart the stack with \`lai-gateway stack-start\`.`);
        return {};
      }
    });
    participant.iconPath = new vscode.ThemeIcon("sparkle");
    context.subscriptions.push(participant);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
