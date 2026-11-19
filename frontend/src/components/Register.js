import React, { useState } from 'react';
import { createAccount } from '../services/api';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await createAccount(email, password);
      window.localStorage.setItem('trading-session', JSON.stringify({
        accessToken: res.access_token,
        refreshToken: res.refresh_token,
      }));
      window.location.href = '/questionnaire';
    } catch (err) {
      setError(err.message || 'Registration failed');
    }
  };

  return (
    <div>
      <h2>Register</h2>
      <form onSubmit={handleSubmit}>
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" required />
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" required />
        {error && <p role="alert">{error}</p>}
        <button type="submit">Register</button>
      </form>
    </div>
  );
};

export default Register;
