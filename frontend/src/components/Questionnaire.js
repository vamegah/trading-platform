import React, { useEffect, useState } from 'react';
import { getStoredSession, evaluateSuitability } from '../services/api';

const Questionnaire = () => {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState('');

  const session = getStoredSession();

  useEffect(() => {
    if (!session?.accessToken) {
      window.location.href = '/login';
      return;
    }
    fetch('/api/profile/questionnaire', {
      headers: { Authorization: `Bearer ${session.accessToken}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText)))
      .then(setQuestions)
      .catch(err => setError(err.message || 'Failed to load questions'));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAnswer = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await evaluateSuitability({ answers });
      window.location.href = '/';
    } catch (err) {
      setError(err.message || 'Submission failed');
    }
  };

  if (!session?.accessToken) return null;

  return (
    <div>
      <h2>Risk Profile Questionnaire</h2>
      <form onSubmit={handleSubmit}>
        {questions.map(q => (
          <div key={q.id}>
            <p>{q.question}</p>
            {q.options.map(opt => (
              <label key={opt.value}>
                <input
                  type="radio"
                  name={q.id}
                  value={opt.value}
                  checked={answers[q.id] === opt.value}
                  onChange={() => handleAnswer(q.id, opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        ))}
        {error && <p role="alert">{error}</p>}
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default Questionnaire;
