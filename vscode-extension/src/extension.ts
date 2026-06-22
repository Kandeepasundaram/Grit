/**
 * Grit VS Code extension entry point.
 *
 * Communicates with the Grit daemon via the same IPC protocol used by
 * the Python CLI — no Python logic is duplicated here.
 */

import * as vscode from "vscode";
import { sendRequest, ping } from "./ipcClient";
import { GritStatusBar } from "./statusBar";

let statusBar: GritStatusBar | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  statusBar = new GritStatusBar();
  statusBar.startAutoRefresh();
  context.subscriptions.push({ dispose: () => statusBar?.dispose() });

  // Refresh on workspace folder changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => statusBar?.refresh())
  );

  // ── Commands ────────────────────────────────────────────────────────────────

  context.subscriptions.push(
    vscode.commands.registerCommand("grit.switchProfile", async () => {
      const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!folder) {
        vscode.window.showWarningMessage("Grit: no workspace folder open.");
        return;
      }

      if (!(await ping())) {
        vscode.window.showErrorMessage(
          "Grit daemon is not running. Start it with: grit daemon start"
        );
        return;
      }

      const resp = await sendRequest("list-profiles");
      const profiles = (resp.payload?.profiles ?? []) as Array<
        Record<string, string>
      >;

      if (!profiles.length) {
        vscode.window.showInformationMessage(
          "No profiles configured. Run `grit profile add` to create one."
        );
        return;
      }

      const picked = await vscode.window.showQuickPick(
        profiles.map((p) => ({
          label: p.name,
          description: p.email,
          id: p.id,
        })),
        { placeHolder: "Select a Git profile", title: "Grit — Switch Profile" }
      );

      if (!picked) return;

      await sendRequest("switch-profile", {
        repo_path: folder,
        profile_id: picked.id,
      });
      await statusBar?.refresh();
      vscode.window.showInformationMessage(
        `Grit: switched to ${picked.label} <${picked.description}>`
      );
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("grit.showSession", async () => {
      const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!folder) return;

      const resp = await sendRequest("get-session", { repo_path: folder });
      const session = resp.payload?.session as Record<string, unknown> | null;

      if (!session) {
        vscode.window.showInformationMessage("Grit: no active session for this repo.");
        return;
      }
      vscode.window.showInformationMessage(
        `Grit session: profile=${session.profile_id}, expires=${session.expires_at}`
      );
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("grit.invalidateSession", async () => {
      const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (!folder) return;

      await sendRequest("delete-session", { repo_path: folder });
      await statusBar?.refresh();
      vscode.window.showInformationMessage("Grit: session cleared.");
    })
  );
}

export function deactivate(): void {
  statusBar?.dispose();
}
