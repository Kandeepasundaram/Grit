/**
 * Synchronous IPC client for talking to the Grit daemon from VS Code.
 * Uses the same newline-delimited JSON protocol as the Python client.
 */

import * as net from "net";
import * as os from "os";
import * as path from "path";

const ENCODING = "utf-8";

function getSocketPath(): string {
  if (process.platform === "win32") {
    return "\\\\.\\pipe\\grit-daemon";
  }
  // Mirror grit.config.paths.ipc_socket_path() logic
  const configDir = process.env.GRIT_CONFIG_DIR;
  if (configDir) {
    return path.join(configDir, "data", "grit.sock");
  }
  // XDG fallback
  const xdgData = process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
  return path.join(xdgData, "grit", "grit.sock");
}

export interface GritResponse {
  status: "ok" | "error";
  payload: Record<string, unknown>;
  error?: string;
}

export function sendRequest(
  type: string,
  payload: Record<string, unknown> = {}
): Promise<GritResponse> {
  return new Promise((resolve, reject) => {
    const socketPath = getSocketPath();
    const client = net.createConnection(socketPath, () => {
      const msg = JSON.stringify({ type, payload }) + "\n";
      client.write(msg, ENCODING);
    });

    let buffer = "";
    client.on("data", (data: Buffer) => {
      buffer += data.toString(ENCODING);
      if (buffer.includes("\n")) {
        client.destroy();
        try {
          resolve(JSON.parse(buffer.trim()) as GritResponse);
        } catch (e) {
          reject(new Error(`Invalid JSON from daemon: ${buffer}`));
        }
      }
    });

    client.on("error", (err: Error) => {
      reject(new Error(`Grit daemon not reachable: ${err.message}`));
    });

    client.setTimeout(3000, () => {
      client.destroy();
      reject(new Error("Grit daemon request timed out"));
    });
  });
}

export async function ping(): Promise<boolean> {
  try {
    const resp = await sendRequest("ping");
    return resp.status === "ok";
  } catch {
    return false;
  }
}
