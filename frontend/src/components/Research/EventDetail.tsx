import React from "react";
import SignalSourceBadge from "./SignalSourceBadge";

interface SourceRef {
  url: string;
  name: string;
  published_at?: string;
}

interface Event {
  event_id: string;
  event_type: string;
  symbol?: string;
  summary?: string;
  confidence?: number;
  source?: string;
  source_refs?: SourceRef[];
  created_at: string;
}

interface Props {
  event: Event;
}

function EventDetail({ event }: Props) {
  return (
    <article className="panel research-event-detail">
      <header>
        <div>
          <span>{event.symbol ?? "—"}</span>
          <strong>{event.event_type.replaceAll("_", " ")}</strong>
        </div>
        {event.source && <SignalSourceBadge source={event.source} confidence={event.confidence} />}
      </header>
      {event.summary && <p>{event.summary}</p>}
      {event.source_refs && event.source_refs.length > 0 && (
        <ul>
          {event.source_refs.map(ref => (
            <li key={ref.url}>
              <a href={ref.url} target="_blank" rel="noreferrer">
                {ref.name}{ref.published_at ? ` · ${ref.published_at}` : ""}
              </a>
            </li>
          ))}
        </ul>
      )}
      <p className="advisor-source-meta">{new Date(event.created_at).toLocaleString()}</p>
    </article>
  );
}

export default EventDetail;
