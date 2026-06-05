import { useState } from 'react';
import PropTypes from 'prop-types';
import { recordChartFeedback } from '../../utils/charts/monitoring';

function ChartFeedbackPanel({ context = 'dashboard' }) {
  const [rating, setRating] = useState('5');
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState('idle');

  const submit = (event) => {
    event.preventDefault();
    recordChartFeedback({
      context,
      rating: Number(rating),
      comment,
    });
    setComment('');
    setStatus('saved');
  };

  return (
    <article className="panel chart-feedback-panel">
      <header>
        <div>
          <span>Chart feedback</span>
          <strong>Release signal</strong>
        </div>
        {status === 'saved' && <span className="badge healthy">saved</span>}
      </header>
      <form className="feedback-grid" onSubmit={submit}>
        <label>
          Rating
          <select value={rating} onChange={(event) => setRating(event.target.value)}>
            <option value="5">5 - Excellent</option>
            <option value="4">4 - Good</option>
            <option value="3">3 - Usable</option>
            <option value="2">2 - Rough</option>
            <option value="1">1 - Blocking</option>
          </select>
        </label>
        <label className="feedback-grid__comment">
          Notes
          <textarea
            maxLength="1000"
            rows="2"
            value={comment}
            onChange={(event) => {
              setComment(event.target.value);
              setStatus('idle');
            }}
          />
        </label>
        <button type="submit">Submit</button>
      </form>
    </article>
  );
}

ChartFeedbackPanel.propTypes = {
  context: PropTypes.string,
};

export default ChartFeedbackPanel;
