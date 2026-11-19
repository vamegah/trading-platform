import React from "react";
import { useResearcherEvents } from "../../hooks/useResearcherEvents";
import EventDetail from "./EventDetail";

interface Props {
  symbol?: string;
}

function EventFeed({ symbol }: Props) {
  const { events, error, loading } = useResearcherEvents(symbol);

  return (
    <section className="panel research-event-feed">
      <header>
        <div>
          <span>Alex Researcher</span>
          <strong>Event Feed{symbol ? ` · ${symbol}` : ""}</strong>
        </div>
        {loading && <span className="badge review">loading</span>}
      </header>
      {error && <p className="advisor-error" role="alert">{error}</p>}
      {!loading && events.length === 0 && !error && (
        <p className="operating-note">No researcher events found.</p>
      )}
      {events.map(event => (
        <EventDetail key={event.event_id} event={event} />
      ))}
    </section>
  );
}

export default EventFeed;
