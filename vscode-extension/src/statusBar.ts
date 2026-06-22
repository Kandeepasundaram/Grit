/**
 * Status bar item showing the current Grit profile.
 * Refreshes every 30 seconds and on workspace folder changes.
 */

import * as vscode from "vscode";
import { sendRequest } from "./ipcClient";

export class GritStatusBar {
  private item: vscode.StatusBarItem;
  private timer: NodeJS.Timeout | undefined;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = "grit.switchProfile";
    this.item.tooltip = "Grit: click to switch Git profile";
  }

  async refresh(): Promise<void> {
    const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!folder) {
      this.item.hide();
      return;
    }

    try {
      const resp = await sendRequest("get-session", { repo_path: folder });
      const session = resp.payload?.session as Record<string, unknown> | null;

      if (!session) {
        this.item.text = "$(person) Grit: no profile";
        this.item.show();
        return;
      }

      // Fetch profile name
      const profilesResp = await sendRequest("list-profiles");
      const profiles = (profilesResp.payload?.profiles ?? []) as Array<
        Record<string, string>
      >;
      const profile = profiles.find((p) => p.id === session.profile_id);
      const label = profile ? profile.name : "Unknown";

      this.item.text = `$(person) ${label}`;
      this.item.show();
    } catch {
      this.item.text = "$(person) Grit: offline";
      this.item.show();
    }
  }

  startAutoRefresh(): void {
    this.refresh();
    this.timer = setInterval(() => this.refresh(), 30_000);
  }

  dispose(): void {
    if (this.timer) {
      clearInterval(this.timer);
    }
    this.item.dispose();
  }
}
