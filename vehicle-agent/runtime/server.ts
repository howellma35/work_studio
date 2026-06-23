/**
 * AutoMind CopilotKit Runtime Server (v2)
 *
 * Architecture: Frontend(Vite:5174) → Runtime(Express:4000) → Python(FastAPI:8001)
 *
 * The Runtime is the official CopilotKit backend layer:
 * - Authentication & security defaults
 * - AG-UI middleware (server-side, tamper-proof)
 * - Agent routing & discovery
 * - Enterprise Intelligence features (threads, inspector)
 *
 * It proxies all CopilotKit requests to the Python backend via HttpAgent.
 */
import express from "express";
import { CopilotSseRuntime } from "@copilotkit/runtime/v2";
import { createCopilotExpressHandler } from "@copilotkit/runtime/v2/express";
import { HttpAgent } from "@ag-ui/client";

// ===== Configuration =====
const PORT = parseInt(process.env.RUNTIME_PORT || "4000", 10);
const PYTHON_AGENT_URL =
  process.env.PYTHON_AGENT_URL || "http://localhost:8001/copilotkit";

// ===== Agent Registration =====
const automindAgent = new HttpAgent({ url: PYTHON_AGENT_URL });

const runtime = new CopilotSseRuntime({
  agents: {
    default: automindAgent,
  },
});

// ===== Express Server =====
const app = express();

// CopilotKit v2 Express handler — returns an Express Router with built-in CORS
const copilotRouter = createCopilotExpressHandler({
  runtime,
  basePath: "/api/copilotkit",
  cors: true, // permissive CORS for dev
});

// Mount the CopilotKit router
app.use(copilotRouter);

// Health check (outside CopilotKit routes)
app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    service: "automind-copilot-runtime",
    python_agent_url: PYTHON_AGENT_URL,
    agents: ["default"],
  });
});

// ===== Start =====
app.listen(PORT, () => {
  console.log(`[Runtime] CopilotKit Runtime running on port ${PORT}`);
  console.log(`[Runtime] Endpoint: http://localhost:${PORT}/api/copilotkit`);
  console.log(`[Runtime] Python agent: ${PYTHON_AGENT_URL}`);
});
