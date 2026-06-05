function AdaptiveNudge({ message = "Review position size before increasing exposure." }) {
  return (
    <article className="panel nudge">
      <span>Adaptive nudge</span>
      <p>{message}</p>
    </article>
  );
}

export default AdaptiveNudge;

