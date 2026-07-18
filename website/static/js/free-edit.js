/* ===========================================================================
   FREE EDIT v2 — PES/FL26 style with zones, position detection, GK lock
   MOBILE-SAFE: document-level listeners with { passive: false }
   =========================================================================== */

var FE = {
  pitch: [],
  bench: [],
  active: false,
  dragging: null,
  pickerEl: null,
  _docHandlers: false,
  _pitchRect: null,

  start: function () {
    this.active = true;
    this.pitch = [];
    this.bench = [];

    var free = window.__FREE_LINEUP__ || {};
    var lineup = window.__LINEUP__ || {};
    var benchKeys = window.__BENCH__ || [];

    var pitchEl = document.getElementById('pitch');
    if (pitchEl) pitchEl.style.overflow = 'visible';

    if (Object.keys(free).length > 0) {
      for (var key in free) {
        if (ROSTER[key]) {
          var p = ROSTER[key];
          if (this.isGK(key)) {
            this.pitch.push({ key: key, x: 0.50, y: 0.90, pos: 'GK' });
          } else {
            this.pitch.push({
              key: key,
              x: free[key].x,
              y: free[key].y,
              pos: free[key].pos || this.calcPos(key, free[key].x, free[key].y),
            });
          }
        }
      }
      this.bench = benchKeys.filter(function (k) { return !free[k]; });
    } else {
      var sel = document.getElementById('formation-select');
      var fmt = sel ? sel.value : '4-3-3';
      var slots = FORMATIONS[fmt] || [];
      var usedKeys = {};
      for (var i = 0; i < slots.length && i < 11; i++) {
        var pkey = lineup[i];
        if (pkey && ROSTER[pkey]) {
          if (this.isGK(pkey)) {
            this.pitch.push({ key: pkey, x: 0.50, y: 0.90, pos: 'GK' });
          } else {
            this.pitch.push({
              key: pkey, x: slots[i].x, y: slots[i].y, pos: slots[i].pos,
            });
          }
          usedKeys[pkey] = true;
        }
      }
      this.bench = benchKeys.filter(function (k) { return !usedKeys[k]; });
    }
    this.render();
  },

  isGK: function (key) {
    var p = ROSTER[key];
    if (!p) return false;
    var pos = (p.pos || p.position || '').toUpperCase();
    return pos === 'GK';
  },

  getZone: function (y) {
    if (y > 0.82) return 'GK';
    if (y > 0.60) return 'DEF';
    if (y > 0.25) return 'MID';
    return 'FWD';
  },

  getSide: function (x) {
    if (x < 0.22) return 'L';
    if (x > 0.78) return 'R';
    return 'C';
  },

  getPosOptions: function (zone, side) {
    var opts = {
      'GK': { 'L': ['GK'], 'C': ['GK'], 'R': ['GK'] },
      'DEF': { 'L': ['LB'], 'C': ['CB'], 'R': ['RB'] },
      'MID': { 'L': ['LM', 'LWF'], 'C': ['CDM', 'CM', 'CAM'], 'R': ['RM', 'RWF'] },
      'FWD': { 'L': ['LWF'], 'C': ['CF', 'SS'], 'R': ['RWF'] },
    };
    return (opts[zone] && opts[zone][side]) || ['CM'];
  },

  calcPos: function (key, x, y) {
    if (this.isGK(key)) return 'GK';
    var zone = this.getZone(y);
    var side = this.getSide(x);
    var options = this.getPosOptions(zone, side);
    return options[0];
  },

  render: function () {
    var pitch = document.getElementById('pitch');
    var label = document.getElementById('formation-label');
    if (label) label.textContent = 'FREE FORMATION - DRAG PLAYERS';
    if (!pitch) return;
    pitch.innerHTML = '';

    // Zone lines
    [{y:25},{y:60},{y:82}].forEach(function(z){
      var line = document.createElement('div');
      line.style.cssText = 'position:absolute;left:0;right:0;top:'+z.y+'%;height:1px;background:rgba(255,206,96,0.06);pointer-events:none;';
      pitch.appendChild(line);
    });

    for (var i = 0; i < this.pitch.length; i++) {
      var pp = this.pitch[i];
      var p = ROSTER[pp.key];
      if (!p) continue;
      var isGK = this.isGK(pp.key);
      var div = document.createElement('div');
      div.className = 'pitch-player';
      div.dataset.key = pp.key;
      div.dataset.fe = '1';
      div.style.left = (pp.x * 100) + '%';
      div.style.top = (pp.y * 100) + '%';
      if (isGK) {
        div.style.cursor = 'not-allowed';
        div.style.opacity = '0.9';
      } else {
        div.style.cursor = 'grab';
        div.style.touchAction = 'none';
      }
      div.innerHTML =
        '<div class="pitch-link">' +
        '<img src="' + p.face_url + '" class="pitch-face" alt="">' +
        '<span class="pitch-player-name">' + p.name + '</span>' +
        '<span class="pitch-player-pos">' + (pp.pos || '') + '</span>' +
        '</div>';
      pitch.appendChild(div);
    }

    var benchEl = document.getElementById('bench-list');
    if (benchEl) {
      benchEl.innerHTML = '';
      this.bench.forEach(function (key) {
        var bp = ROSTER[key];
        if (!bp) return;
        var bdiv = document.createElement('div');
        bdiv.className = 'bench-player';
        bdiv.dataset.key = key;
        bdiv.dataset.fe = '1';
        bdiv.style.cursor = 'grab';
        bdiv.style.touchAction = 'none';
        bdiv.innerHTML =
          '<img src="' + bp.face_url + '" class="bench-face" alt="">' +
          '<span class="bench-name">' + bp.name + '</span>' +
          '<span class="bench-pos">' + (bp.pos || '') + '</span>';
        benchEl.appendChild(bdiv);
      });
    }
    if (this.active) this.attachHandlers();
  },

  attachHandlers: function () {
    var self = this;
    var pitch = document.getElementById('pitch');

    document.querySelectorAll('[data-fe="1"]').forEach(function (el) {
      var isThisGK = self.isGK(el.dataset.key);

      el.addEventListener('pointerdown', function (e) {
        e.preventDefault();
        FE._pitchRect = pitch.getBoundingClientRect();
        self.removePicker();
        self.dragging = {
          key: el.dataset.key,
          el: el,
          isPitch: el.classList.contains('pitch-player'),
          isGK: isThisGK,
          moved: false,
          overPitch: false,
        };
        try { el.setPointerCapture(e.pointerId); } catch (err) {}
        el.style.zIndex = '1000';
        el.style.opacity = '0.85';
        el.style.touchAction = 'none';
      }, { passive: false });
    });

    if (!FE._docHandlers) {
      FE._docHandlers = true;

      // pointermove on DOCUMENT (not element) — critical for mobile where
      // the finger slides off the original element during drag.
      // { passive: false } so preventDefault actually blocks page scroll.
      document.addEventListener('pointermove', function (e) {
        if (!FE.dragging) return;
        e.preventDefault();
        var rect = FE._pitchRect;
        var el = FE.dragging.el;
        var px = e.clientX - rect.left;
        var py = e.clientY - rect.top;
        // GK special: allow visual drag anywhere but never place on pitch
        if (FE.dragging.isGK) {
          el.style.left = Math.max(0, Math.min(100, (px / rect.width) * 100)) + '%';
          el.style.top = Math.max(0, Math.min(100, (py / rect.height) * 100)) + '%';
          FE.dragging.moved = true;
          FE.dragging.overPitch = false;
          return;
        }
        if (px >= 0 && px <= rect.width && py >= 0 && py <= rect.height) {
          var yPct = py / rect.height;
          if (yPct > 0.82) return;
          var x = Math.max(0.03, Math.min(0.97, px / rect.width));
          var y = Math.max(0.03, Math.min(0.78, py / rect.height));
          el.style.left = (x * 100) + '%';
          el.style.top = (y * 100) + '%';
          FE.dragging.moved = true;
          FE.dragging.overPitch = true;
          FE.dragging.x = x;
          FE.dragging.y = y;
        } else {
          FE.dragging.overPitch = false;
        }
      }, { passive: false });

      document.addEventListener('pointerup', function (e) {
        if (!FE.dragging) return;
        var el = FE.dragging.el;
        try { el.releasePointerCapture(e.pointerId); } catch (err) {}
        el.style.zIndex = '';
        el.style.opacity = '';
        var key = FE.dragging.key;
        var wasPitch = FE.dragging.isPitch;
        var isPitch = FE.dragging.overPitch;
        if (FE.dragging.moved) {
          if (FE.dragging.isGK) {
            // GK special handling on drop
            var rect2 = FE._pitchRect;
            var px2 = e.clientX - rect2.left;
            var py2 = e.clientY - rect2.top;
            var onPitch = (px2 >= 0 && px2 <= rect2.width && py2 >= 0 && py2 <= rect2.height);
            if (!onPitch) {
              // Dropped outside pitch -> bench (sub)
              FE.moveToBench(key); FE.dragging = null; FE.render();
            } else if (!wasPitch) {
              // Bench GK dropped ON pitch -> only allow if no GK already on pitch
              var gkAlready = false;
              for (var gi = 0; gi < FE.pitch.length; gi++) {
                if (FE.isGK(FE.pitch[gi].key)) { gkAlready = true; break; }
              }
              if (!gkAlready && FE.pitch.length < 11) {
                // Move GK to its locked position (0.50, 0.90)
                FE.bench = FE.bench.filter(function(k){ return k !== key; });
                FE.pitch.push({ key: key, x: 0.50, y: 0.90, pos: 'GK' });
                FE.dragging = null; FE.render();
              } else {
                // GK already on pitch or squad full -> snap back
                FE.dragging = null; FE.render();
              }
            } else {
              // Pitch GK dropped on pitch -> snap back to GK spot
              FE.dragging = null; FE.render();
            }
          } else if (wasPitch && !isPitch) {
            FE.moveToBench(key); FE.dragging = null; FE.render();
          } else if (!wasPitch && isPitch) {
            FE.moveToPitch(key, FE.dragging.x, FE.dragging.y);
            FE.dragging = null; FE.render(); FE.maybeShowPicker(key);
          } else if (wasPitch && isPitch) {
            FE.updatePosition(key, FE.dragging.x, FE.dragging.y);
            FE.dragging = null; FE.render(); FE.maybeShowPicker(key);
          }
        } else { FE.dragging = null; }
      }, { passive: false });

      document.addEventListener('pointercancel', function () {
        if (!FE.dragging) return;
        FE.dragging.el.style.zIndex = '';
        FE.dragging.el.style.opacity = '';
        FE.dragging = null;
      }, { passive: false });

      // iOS Safari fallback: explicitly block touch scroll during drag
      document.addEventListener('touchmove', function (e) {
        if (FE.dragging) e.preventDefault();
      }, { passive: false });
    }
  },

  maybeShowPicker: function (key) {
    var pp = null;
    for (var i = 0; i < this.pitch.length; i++) {
      if (this.pitch[i].key === key) { pp = this.pitch[i]; break; }
    }
    if (!pp) return;
    var zone = this.getZone(pp.y);
    var side = this.getSide(pp.x);
    var options = this.getPosOptions(zone, side);
    if (zone === 'FWD' && side === 'C') {
      var cfCount = 0;
      for (var j = 0; j < this.pitch.length; j++) {
        if (this.pitch[j].key === key) continue;
        if (['CF'].indexOf(this.pitch[j].pos || '') >= 0) cfCount++;
      }
      if (cfCount === 0) options = ['CF'];
    }
    if (options.length <= 1) { pp.pos = options[0]; this.render(); return; }
    if (options.indexOf(pp.pos) >= 0) return;
    this.showPicker(key, pp, options);
  },

  showPicker: function (key, pp, options) {
    var self = this;
    this.removePicker();
    var pitch = document.getElementById('pitch');
    var picker = document.createElement('div');
    picker.className = 'fe-pos-picker';
    picker.style.left = (pp.x * 100) + '%';
    picker.style.top = (pp.y * 100) + '%';
    picker.innerHTML = '<div class="fe-picker-title">' + (ROSTER[key] ? ROSTER[key].name : '') + '</div>';
    options.forEach(function (opt) {
      var btn = document.createElement('button');
      btn.className = 'fe-picker-btn';
      btn.textContent = opt;
      btn.onclick = function (e) { e.preventDefault(); e.stopPropagation(); pp.pos = opt; self.removePicker(); self.render(); };
      picker.appendChild(btn);
    });
    var closeBtn = document.createElement('button');
    closeBtn.className = 'fe-picker-close';
    closeBtn.textContent = 'X';
    closeBtn.onclick = function (e) { e.preventDefault(); self.removePicker(); self.render(); };
    picker.appendChild(closeBtn);
    pitch.appendChild(picker);
    this.pickerEl = picker;
  },

  removePicker: function () {
    if (this.pickerEl) { this.pickerEl.remove(); this.pickerEl = null; }
  },

  updatePosition: function (key, x, y) {
    for (var i = 0; i < this.pitch.length; i++) {
      if (this.pitch[i].key === key) {
        this.pitch[i].x = x;
        this.pitch[i].y = y;
        var zone = this.getZone(y);
        var side = this.getSide(x);
        var options = this.getPosOptions(zone, side);
        if (options.length === 1) this.pitch[i].pos = options[0];
        return;
      }
    }
  },

  moveToPitch: function (key, x, y) {
    if (this.pitch.length >= 11) return;
    this.bench = this.bench.filter(function (k) { return k !== key; });
    var pos = this.calcPos(key, x, y);
    this.pitch.push({ key: key, x: x, y: y, pos: pos });
  },

  moveToBench: function (key) {
    this.pitch = this.pitch.filter(function (p) { return p.key !== key; });
    if (this.bench.indexOf(key) === -1) this.bench.push(key);
  },

  getPositions: function () {
    var pos = {};
    for (var i = 0; i < this.pitch.length; i++) {
      pos[this.pitch[i].key] = {
        x: this.pitch[i].x, y: this.pitch[i].y, pos: this.pitch[i].pos || '',
      };
    }
    return pos;
  },
};

// Read-only render for visitors
document.addEventListener('DOMContentLoaded', function () {
  if (window.__IS_OWNER__) return;
  var free = window.__FREE_LINEUP__ || {};
  if (Object.keys(free).length === 0) return;
  var pitch = document.getElementById('pitch');
  if (!pitch) return;
  var label = document.getElementById('formation-label');
  if (label) label.textContent = 'CUSTOM FORMATION';
  pitch.style.overflow = 'visible';
  pitch.innerHTML = '';
  for (var key in free) {
    var p = ROSTER[key];
    if (!p) continue;
    var pos = free[key];
    var div = document.createElement('div');
    div.className = 'pitch-player';
    div.style.left = (pos.x * 100) + '%';
    div.style.top = (pos.y * 100) + '%';
    div.innerHTML =
      '<a href="/player/' + key + '" class="pitch-link">' +
      '<img src="' + p.face_url + '" class="pitch-face" alt="">' +
      '<span class="pitch-player-name">' + p.name + '</span>' +
      '<span class="pitch-player-pos">' + (pos.pos || p.pos || '') + '</span></a>';
    pitch.appendChild(div);
  }
  var benchEl = document.getElementById('bench-list');
  if (!benchEl) return;
  var bench = (window.__BENCH__ || []).filter(function (k) { return !free[k]; });
  benchEl.innerHTML = '';
  bench.forEach(function (key) {
    var bp = ROSTER[key];
    if (!bp) return;
    var bdiv = document.createElement('a');
    bdiv.href = '/player/' + key;
    bdiv.className = 'bench-player';
    bdiv.innerHTML =
      '<img src="' + bp.face_url + '" class="bench-face" alt="">' +
      '<span class="bench-name">' + bp.name + '</span>' +
      '<span class="bench-pos">' + (bp.pos || '') + '</span>';
    benchEl.appendChild(bdiv);
  });
});
