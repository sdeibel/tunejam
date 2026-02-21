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
      var href = link.getAttribute('href');
      var title = extractTitle(link);
      play(href, title);
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

  function play(url, title) {
    cancelAnimationFrame(rafId);
    audio.src = url;
    audio.playbackRate = parseFloat(speedSelect.value);
    audio.play();
    titleEl.textContent = title;
    btnPlay.textContent = '\u23F8';
    progressFill.style.width = '0%';
    timeEl.textContent = '0:00 / 0:00';
    player.style.display = 'flex';
    tick();
  }

  function hide() {
    cancelAnimationFrame(rafId);
    audio.pause();
    audio.src = '';
    player.style.display = 'none';
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
