// Next.js API route support: https://nextjs.org/docs/api-routes/introduction
import type { NextApiRequest, NextApiResponse } from "next";
import { v4 } from "uuid";
import { AccessToken } from "livekit-server-sdk";

export type ConnectionDetailsParams = {
  agent_type: string;
};

export type ConnectionDetails = {
  token: string;
  ws_url: string;
};

type ErrorResponse = {
  error: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ConnectionDetails | ErrorResponse>
) {
  if (req.method !== "GET") {
    return res.status(400).json({ error: "Invalid method" });
  }

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const wsUrl = process.env.LIVEKIT_WS_URL;

  if (!apiKey || !apiSecret || !wsUrl) {
    return res.status(500).json({ error: "Server misconfigured" });
  }

  const agent_type = req.query.agent_type;
  if (!agent_type) {
    return res.status(400).json({ error: "Invalid or missing agent_type" });
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: agent_type + "-" + v4(),
  });

  const room = "test";

  at.addGrant({ room, roomJoin: true, canPublish: true, canSubscribe: true });
  res.status(200).json({ token: at.toJwt(), ws_url: wsUrl });
}
