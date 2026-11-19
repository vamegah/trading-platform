import React from "react";

interface Props {
  source: string;
  confidence?: number;
}

function SignalSourceBadge({ source, confidence }: Props) {
  return (
    <span className="badge healthy" title={confidence != null ? `Confidence: ${confidence}%` : undefined}>
      {source}
      {confidence != null && <> · {confidence}%</>}
    </span>
  );
}

export default SignalSourceBadge;
