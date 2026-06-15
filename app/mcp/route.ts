import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 1800;

const MCP_TARGET = (
  process.env.KIWI_KK_MCP_TARGET_URL ||
  process.env.KK_API_INTERNAL_URL ||
  "http://localhost:8788"
).replace(/\/$/, "");
const PROXY_TIMEOUT_SECONDS = Number(process.env.KK_API_PROXY_TIMEOUT_SECONDS || 1800);

export async function POST(request: NextRequest) {
  return proxyMcp(request);
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}

async function proxyMcp(request: NextRequest) {
  const started = Date.now();
  const targetUrl = `${MCP_TARGET}/mcp`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Math.max(1, PROXY_TIMEOUT_SECONDS) * 1000);

  try {
    console.log(`[kiwi-mcp-proxy] start method=${request.method} path=/mcp`);
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: proxyHeaders(request.headers),
      body: await request.arrayBuffer(),
      signal: controller.signal,
    });
    console.log(`[kiwi-mcp-proxy] done status=${response.status} elapsedMs=${Date.now() - started}`);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders(response.headers),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[kiwi-mcp-proxy] failed elapsedMs=${Date.now() - started} error=${message}`);
    return Response.json(
      {
        detail: "KIWI KK MCP proxy failed",
        target: targetUrl,
        error: message,
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

function proxyHeaders(headers: Headers) {
  const result = new Headers(headers);
  for (const key of ["host", "connection", "content-length", "accept-encoding"]) {
    result.delete(key);
  }
  return result;
}

function responseHeaders(headers: Headers) {
  const result = new Headers(headers);
  for (const key of ["content-encoding", "content-length", "transfer-encoding", "connection"]) {
    result.delete(key);
  }
  result.set("Access-Control-Allow-Origin", "*");
  return result;
}
