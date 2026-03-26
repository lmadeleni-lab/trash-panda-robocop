import { Type } from "@sinclair/typebox";
import { definePluginEntry } from "openclaw/plugin-sdk";

type PluginConfig = {
  baseUrl: string;
  apiKey: string;
  requestTimeoutMs?: number;
};

type TextResult = {
  content: Array<{ type: "text"; text: string }>;
};

function toTextResult(payload: unknown): TextResult {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2),
      },
    ],
  };
}

async function requestJson(
  config: PluginConfig,
  path: string,
  init?: RequestInit,
): Promise<unknown> {
  const controller = new AbortController();
  const timeoutMs = config.requestTimeoutMs ?? 5000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(new URL(path, config.baseUrl), {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": config.apiKey,
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`trash-panda Robocop request failed: ${response.status} ${body}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}

export default definePluginEntry((api) => {
  api.registerTool(
    "trash_panda_briefing",
    {
      title: "trash-panda briefing",
      description:
        "Fetch a bounded operator briefing from the Raspberry Pi field node for OpenClaw review.",
      inputSchema: Type.Object({
        limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 50, default: 10 })),
        date: Type.Optional(
          Type.String({
            description: "Optional local date in YYYY-MM-DD form for the nightly summary.",
          }),
        ),
      }),
    },
    async (_toolId, params, ctx) => {
      const config = ctx.plugin.config as PluginConfig;
      const query = new URLSearchParams();
      if (params.limit !== undefined) {
        query.set("limit", String(params.limit));
      }
      if (params.date !== undefined) {
        query.set("date", params.date);
      }
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      const payload = await requestJson(config, `/agent/opencclaw/briefing${suffix}`);
      return toTextResult(payload);
    },
  );

  api.registerTool(
    "trash_panda_list_strategies",
    {
      title: "trash-panda strategies",
      description: "List the approved strategy catalog and current recommendation map.",
      inputSchema: Type.Object({}),
    },
    async (_toolId, _params, ctx) => {
      const config = ctx.plugin.config as PluginConfig;
      const payload = await requestJson(config, "/strategies");
      return toTextResult(payload);
    },
  );

  api.registerTool(
    "trash_panda_get_summary",
    {
      title: "trash-panda nightly summary",
      description: "Read a nightly summary from the Raspberry Pi field node.",
      inputSchema: Type.Object({
        date: Type.String({
          description: "Local date in YYYY-MM-DD form.",
        }),
      }),
    },
    async (_toolId, params, ctx) => {
      const config = ctx.plugin.config as PluginConfig;
      const suffix = `?date=${encodeURIComponent(params.date)}`;
      const payload = await requestJson(config, `/summary/nightly${suffix}`);
      return toTextResult(payload);
    },
  );

  api.registerTool(
    "trash_panda_set_strategy",
    {
      title: "trash-panda set strategy",
      description:
        "Set the next approved strategy on the Raspberry Pi field node. Safety policy still applies at event time.",
      inputSchema: Type.Object({
        strategy_name: Type.String({
          description:
            "One of LIGHT_ONLY, LIGHT_SOUND, WATER_ONLY, LIGHT_WATER, SOUND_LIGHT_WATER, LIGHT_SOUND_WATER_PAN.",
        }),
      }),
    },
    async (_toolId, params, ctx) => {
      const config = ctx.plugin.config as PluginConfig;
      const payload = await requestJson(config, "/strategies/select", {
        method: "POST",
        body: JSON.stringify({ strategy_name: params.strategy_name }),
      });
      return toTextResult(payload);
    },
    { optional: true },
  );
});
