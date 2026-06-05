import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const Questionnaire = () => {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const navigate = useNavigate();
  const token = localStorage.getItem('access_token');

  useEffect(() => {
    const fetchQuestions = async () => {
      const res = await axios.get('/api/profile/questionnaire', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQuestions(res.data);
    };
    fetchQuestions();
  }, [token]);

  const handleAnswer = (questionId, value) => {
    setAnswers({ ...answers, [questionId]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/profile/questionnaire', { answers }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      navigate('/');
    } catch (err) {
      alert('Submission failed');
    }
  };

  if (!token) {
    navigate('/login');
    return null;
  }

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
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default Questionnaire;