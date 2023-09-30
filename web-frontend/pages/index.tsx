import { useCallback, useEffect, useRef, useState } from "react";
import { ConnectionDetails } from "./api/connection_details";
import { LiveKitRoom, ParticipantLoop, RoomAudioRenderer, TrackToggle, VideoConference, useLocalParticipant, useMediaTrack, useParticipantContext, useParticipantInfo, useRemoteParticipants } from "@livekit/components-react";
import "@livekit/components-styles";
import axios from "axios";
import { DataPacket_Kind, Track } from "livekit-client";

export default function Page() {
  const [connectionDetails, setConnectionDetails] =
    useState<ConnectionDetails | null>(null);

  useEffect(() => {
    axios
      .get<ConnectionDetails>("/api/connection_details")
      .then((r) => setConnectionDetails(r.data));
  }, []);

  if (!connectionDetails) {
    return <div></div>;
  }

  return (
    <LiveKitRoom
      data-lk-theme="default"
      serverUrl={connectionDetails.ws_url}
      token={connectionDetails.token}
    >
      <div className="flex-col p-0">
        {/* <DataSender /> */}
        <Kitt />
      </div>
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function Kitt() {
  const participants = useRemoteParticipants();
  const addKitt = useCallback(async () => {
    const res = await axios.post("http://localhost:8000/add_agent", {
      agent: "kitt",
    });
    console.log(res);
  }, []);

  return (
    <div>
      <TrackToggle source={Track.Source.Microphone} />
      <button onClick={addKitt}>
        Add Kitt
      </button>
      <ParticipantLoop participants={participants}>
        <Agent />
      </ParticipantLoop>
    </div>
  )
}

function Agent() {
  const participant = useParticipantContext();
  const { identity, metadata } = useParticipantInfo({ participant });

  return (
    <div className="flex flex-col">
      {identity}
      {metadata}
    </div>
  )
}
