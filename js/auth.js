/**
 * auth.js — Login/Signup Page logic (No Modals)
 */

function openLoginModal() {
  window.location.href = '/login';
}

function openSignupModal() {
  window.location.href = '/signup';
}

function togglePassword(inputId, btnEl) {
  const input = document.getElementById(inputId);
  if (!input) return;
  
  if (input.type === 'password') {
    input.type = 'text';
    btnEl.innerHTML = Icons.eyeOff; 
  } else {
    input.type = 'password';
    btnEl.innerHTML = Icons.eye; 
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  setLoading(btn, true, 'Signing in...');
  
  try {
    const data = await API.post('/auth/login', {
      email: document.getElementById('login-email').value,
      password: document.getElementById('login-password').value
    });
    
    Auth.setSession(data.access_token, data.user);
    Toast.success(`Welcome back, ${data.user.name.split(' ')[0]}!`);
    
    setTimeout(() => {
      // Role based redirection
      if (data.user.role === 'admin') {
        window.location.href = '/admin';
      } else {
        window.location.href = '/dashboard';
      }
    }, 600);
  } catch (err) {
    Toast.error(err.message);
  } finally {
    setLoading(btn, false);
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const btn = document.getElementById('signup-btn');
  const password = document.getElementById('signup-password').value;
  
  if (password.length < 6) {
    Toast.error('Password must be at least 6 characters');
    return;
  }
  
  setLoading(btn, true, 'Creating account...');
  
  try {
    const data = await API.post('/auth/signup', {
      name: document.getElementById('signup-name').value,
      email: document.getElementById('signup-email').value,
      password: password
    });
    
    Auth.setSession(data.access_token, data.user);
    Toast.success(`Welcome, ${data.user.name}!`);
    
    setTimeout(() => {
      window.location.href = '/dashboard';
    }, 600);
  } catch (err) {
    Toast.error(err.message);
  } finally {
    setLoading(btn, false);
  }
}