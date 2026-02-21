/* Element.closest polyfill for older browsers */
if (!Element.prototype.closest) {
  Element.prototype.closest = function(s) {
    var el = this;
    do {
      if (el.matches ? el.matches(s) : el.msMatchesSelector(s)) return el;
      el = el.parentElement || el.parentNode;
    } while (el !== null && el.nodeType === 1);
    return null;
  };
}

/* Magic-link login popup */
(function() {
  var overlay = null;
  var emailInput = null;
  var targetInput = null;
  var submitBtn = null;
  var messageEl = null;

  function init() {
    overlay = document.getElementById('login-overlay');
    if (!overlay) return;

    emailInput = document.getElementById('login-email');
    targetInput = document.getElementById('login-target');
    submitBtn = document.getElementById('login-submit');
    messageEl = document.getElementById('login-message');

    var closeBtn = document.getElementById('login-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', hideLoginPopup);
    }

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) hideLoginPopup();
    });

    if (submitBtn) {
      submitBtn.addEventListener('click', submitLogin);
    }

    if (emailInput) {
      emailInput.addEventListener('keydown', function(e) {
        if (e.keyCode === 13) {
          e.preventDefault();
          submitLogin();
        }
      });
    }

    document.addEventListener('keydown', function(e) {
      if (e.keyCode === 27 && overlay.style.display !== 'none') {
        hideLoginPopup();
      }
    });

    /* Delegate clicks on login trigger buttons */
    document.addEventListener('click', function(e) {
      var btn = e.target.closest('[data-login-target]');
      if (btn) {
        e.preventDefault();
        showLoginPopup(btn.getAttribute('data-login-target'));
      }
    });
  }

  function showLoginPopup(target) {
    if (!overlay) return;
    targetInput.value = target || '/events';
    emailInput.value = '';
    messageEl.textContent = '';
    messageEl.className = '';
    submitBtn.disabled = false;
    overlay.style.display = 'flex';
    emailInput.focus();
  }

  function hideLoginPopup() {
    if (overlay) overlay.style.display = 'none';
  }

  function submitLogin() {
    var email = emailInput.value.trim();
    if (!email || email.indexOf('@') === -1) {
      messageEl.textContent = 'Please enter a valid email address.';
      messageEl.className = 'error';
      return;
    }

    submitBtn.disabled = true;
    messageEl.textContent = 'Sending...';
    messageEl.className = '';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/auth/send', true);
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    xhr.onreadystatechange = function() {
      if (xhr.readyState !== 4) return;
      try {
        var resp = JSON.parse(xhr.responseText);
        messageEl.textContent = resp.message;
        messageEl.className = resp.ok ? 'success' : 'error';
        if (!resp.ok) submitBtn.disabled = false;
      } catch(e) {
        messageEl.textContent = 'An error occurred. Please try again.';
        messageEl.className = 'error';
        submitBtn.disabled = false;
      }
    };
    xhr.send('email=' + encodeURIComponent(email) + '&target=' + encodeURIComponent(targetInput.value));
  }

  /* Expose globally for /authorize compatibility route */
  window.showLoginPopup = function(target) {
    if (overlay) {
      showLoginPopup(target);
    } else {
      /* If called before init, defer */
      document.addEventListener('DOMContentLoaded', function() {
        init();
        showLoginPopup(target);
      });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
