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

/* Floating audio player - intercepts recording links and plays in-page */
(function() {
  var audio = null;
  var player = null;
  var btnPlay = null;
  var titleEl = null;
  var progressTrack = null;
  var progressFill = null;
  var timeEl = null;
  var rafId = null;
  var speedSelect = null;
  var currentLink = null;  // The <a> element currently playing

  function init() {
    player = document.getElementById('audio-player');
    if (!player) return;
    btnPlay = player.querySelector('.ap-play');
    titleEl = player.querySelector('.ap-title');
    progressTrack = player.querySelector('.ap-progress-track');
    progressFill = player.querySelector('.ap-progress-fill');
    timeEl = player.querySelector('.ap-time');

    audio = new Audio();
    audio.preload = 'metadata';

    audio.addEventListener('ended', function() {
      hide();
    });
    audio.addEventListener('loadedmetadata', function() {
      updateTime();
    });

    btnPlay.addEventListener('click', function() {
      if (audio.paused) {
        audio.play();
        btnPlay.textContent = '\u23F8';
      } else {
        audio.pause();
        btnPlay.textContent = '\u25B6';
      }
    });

    progressTrack.addEventListener('click', function(e) {
      if (!audio.duration) return;
      var rect = progressTrack.getBoundingClientRect();
      var ratio = (e.clientX - rect.left) / rect.width;
      audio.currentTime = ratio * audio.duration;
    });

    speedSelect = player.querySelector('.ap-speed');
    speedSelect.addEventListener('change', function() {
      audio.playbackRate = parseFloat(speedSelect.value);
    });

    player.querySelector('.ap-close').addEventListener('click', function() {
      hide();
    });

    // Event delegation: intercept clicks on recording links
    document.addEventListener('click', function(e) {
      var link = e.target.closest('a[href^="/recording/"]');
      if (!link) return;
      e.preventDefault();
      // Toggle: click same link again to stop
      if (currentLink === link) {
        hide();
        return;
      }
      var href = link.getAttribute('href');
      var title = extractTitle(link);
      play(href, title, link);
    });
  }

  function extractTitle(link) {
    // 1. Look for nearest h1 or h2 ancestor
    var el = link.parentElement;
    while (el && el !== document.body) {
      if (el.tagName === 'H1' || el.tagName === 'H2') {
        // Get text content before the dash separator (title - key)
        var text = '';
        for (var i = 0; i < el.childNodes.length; i++) {
          var node = el.childNodes[i];
          if (node.nodeType === 3) { // text node
            text += node.textContent;
          }
        }
        text = text.replace(/\s*-\s*$/, '').trim();
        if (text) return text;
      }
      el = el.parentElement;
    }

    // 2. Walk previous siblings to find nearest /tune/ link
    var sib = link.previousElementSibling;
    while (sib) {
      if (sib.tagName === 'A' && sib.getAttribute('href') &&
          sib.getAttribute('href').indexOf('/tune/') === 0) {
        var t = sib.textContent.trim();
        if (t) return t;
      }
      sib = sib.previousElementSibling;
    }

    // 3. Fallback: extract from URL
    var href = link.getAttribute('href');
    var name = href.replace('/recording/', '');
    return name.replace(/_/g, ' ').replace(/\b\w/g, function(c) {
      return c.toUpperCase();
    });
  }

  function setLinkPlaying(link) {
    clearLinkPlaying();
    currentLink = link;
    if (link) link.classList.add('ap-link-playing');
  }

  function clearLinkPlaying() {
    if (currentLink) currentLink.classList.remove('ap-link-playing');
    currentLink = null;
  }

  function play(url, title, link) {
    cancelAnimationFrame(rafId);
    clearLinkPlaying();
    // Notify other players (e.g. ABC synth) that recording is starting
    document.dispatchEvent(new Event('audioPlayerStart'));
    audio.src = url;
    audio.playbackRate = parseFloat(speedSelect.value);
    audio.play();
    titleEl.textContent = title;
    btnPlay.textContent = '\u23F8';
    progressFill.style.width = '0%';
    timeEl.textContent = '0:00 / 0:00';
    player.style.display = 'flex';
    setLinkPlaying(link);
    tick();
  }

  function hide() {
    cancelAnimationFrame(rafId);
    audio.pause();
    audio.src = '';
    player.style.display = 'none';
    clearLinkPlaying();
  }

  function tick() {
    updateTime();
    rafId = requestAnimationFrame(tick);
  }

  function updateTime() {
    var cur = audio.currentTime || 0;
    var dur = audio.duration || 0;
    if (dur && isFinite(dur)) {
      progressFill.style.width = (cur / dur * 100) + '%';
      timeEl.textContent = fmt(cur) + ' / ' + fmt(dur);
    } else {
      progressFill.style.width = '0%';
      timeEl.textContent = fmt(cur) + ' / 0:00';
    }
  }

  function fmt(s) {
    var m = Math.floor(s / 60);
    var sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  // Expose API for other scripts to stop/query the recording player
  window.audioPlayerStop = function() { if (player) hide(); };
  window.audioPlayerPlaying = function() { return !!currentLink; };

  // Stop playback when navigating away (including browser back button)
  window.addEventListener('pagehide', function() {
    if (currentLink) hide();
  });

  // Fade in uncached images; show cached images immediately
  function initImageFadeIn() {
    var imgs = document.querySelectorAll('#header img, img.eye-candy');
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      if (img.complete) {
        img.classList.add('loaded');
      } else {
        img.classList.add('fadein');
        img.addEventListener('load', function() {
          this.classList.add('loaded');
        });
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      init();
      initImageFadeIn();
    });
  } else {
    init();
    initImageFadeIn();
  }
})();
