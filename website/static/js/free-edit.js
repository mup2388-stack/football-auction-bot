/* ===========================================================================
   FREE EDIT v2 — PES/FL26 style with zones, position detection, GK lock
   ===========================================================================

   Zones (based on Y position):
     y > 0.75       → GK zone (LOCKED — only GK can be here, nobody enters)
     0.50 < y ≤ 0.75 → DEF zone
     0.25 < y ≤ 0.50 → MID zone
     y ≤ 0.25        → FWD zone

   Sides (based on X position):
     x < 0.33   → Left
     0.33-0.67  → Center
     x > 0.67   → Right

   Position mapping (zone + side → options):
     GK+C  → GK (locked)
     DEF+L → LB
     DEF+C → CB
     DEF+R → RB
     MID+L → LM / LW (choose)
     MID+C → CDM / CM / CAM (choose)
     MID+R → RM / RW (choose)
     FWD+L → LW / LF (choose)
     FWD+C → ST / CF / SS (SS if another ST exists)
     FWD+R → RW / RF (choose)
   =========================================================================== */

var FE = {
  pitch: [],
  bench: [],
  active: false,
  dragging: null,
  pickerEl: null,

  start: function () {
    this.active = true;
    this.pitch = [];
    this.bench = [];

    var free = window.__FREE_LINEUP__ || {};
    var lineup = window.__LINEUP__ || {};
    var benchKeys = window.__BENCH__ || [];

    // Temporarily allow overflow on pitch so picker popups aren't clipped
    var pitchEl = document.getElementById('pitch');
    if (pitchEl) pitchEl.style.overflow = 'visible';

    if (Object.keys(free).length > 0) {
      for (var key in free) {
        if (ROSTER[key]) {
          var p = ROSTER[key];
          // Lock GK to center of GK zone
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
          // Lock GK to center of GK zone
          if (this.isGK(pkey)) {
            this.pitch.push({ key: pkey, x: 0.50, y: 0.90, pos: 'GK' });
          } else {
            this.pitch.push({
              key: pkey,
              x: slots[i].x,
              y: slots[i].y,
              pos: slots[i].pos,
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

  // Returns array of position options for a zone+side
  getPosOptions: function (zone, side) {
    var opts = {
      'GK': { 'L': ['GK'], 'C': ['GK'], 'R': ['GK'] },
      'DEF': { 'L': ['LB'], 'C': ['CB'], 'R': ['RB'] },
      'MID': { 'L': ['LM', 'LWF'], 'C': ['CDM', 'CM', 'CAM'], 'R': ['RM', 'RWF'] },
      'FWD': { 'L': ['LWF'], 'C': ['CF', 'SS'], 'R': ['RWF'] },
    };
    return (opts[zone] && opts[zone][side]) || ['CM'];
  },

  // Auto-calculate position (first option) for a player at x,y
  calcPos: function (key, x, y) {
    if (this.isGK(key)) return 'GK';
    var zone = this.getZone(y);
    var side = this.getSide(x);
    var options = this.getPosOptions(zone, side);
    return options[0];
  },

  // Check if two position options need a picker (more than 1 option)
  needsPicker: function (zone, side) {
    return this.getPosOptions(zone, side).length > 1;
  },

  render: function () {
    var pitch = document.getElementById('pitch');
    var label = document.getElementById('formation-label');
    if (label) label.textContent = 'FREE FORMATION - DRAG PLAYERS';
    if (!pitch) return;
    pitch.innerHTML = '';

    // Draw faint zone lines
    var zones = [
      { y: 25, label: 'FWD' },
      { y: 60, label: 'MID' },
      { y: 82, label: 'DEF' },
    ];
    zones.forEach(function (z) {
      var line = document.createElement('div');
      line.style.cssText = 'position:absolute;left:0;right:0;top:' + z.y + '%;height:1px;background:rgba(255,206,96,0.06);pointer-events:none;';
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

    // Render bench
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
    var pitchRect = null;

    document.querySelectorAll('[data-fe="1"]').forEach(function (el) {
      // GK can't be dragged
      if (self.isGK(el.dataset.key)) return;

      el.addEventListener('pointerdown', function (e) {
        e.preventDefault();
        pitchRect = pitch.getBoundingClientRect();
        self.removePicker();
        self.dragging = {
          key: el.dataset.key,
          el: el,
          isPitch: el.classList.contains('pitch-player'),
          moved: false,
          overPitch: false,
        };
        el.setPointerCapture(e.pointerId);
        el.style.zIndex = '1000';
        el.style.opacity = '0.85';
      });

      el.addEventListener('pointermove', function (e) {
        if (!self.dragging || self.dragging.el !== el) return;
        e.preventDefault();

        var px = e.clientX - pitchRect.left;
        var py = e.clientY - pitchRect.top;

        if (px >= 0 && px <= pitchRect.width && py >= 0 && py <= pitchRect.height) {
          // Block entering GK zone for non-GK players
          var yPct = py / pitchRect.height;
          if (yPct > 0.82) return; // can't enter GK zone

          var x = Math.max(0.03, Math.min(0.97, px / pitchRect.width));
          var y = Math.max(0.03, Math.min(0.78, py / pitchRect.height)); // cap just below GK zone
          el.style.left = (x * 100) + '%';
          el.style.top = (y * 100) + '%';
          self.dragging.moved = true;
          self.dragging.overPitch = true;
          self.dragging.x = x;
          self.dragging.y = y;
        } else {
          self.dragging.overPitch = false;
        }
      });

      var finishDrag = function (e) {
        if (!self.dragging || self.dragging.el !== el) return;
        el.releasePointerCapture(e.pointerId);
        el.style.zIndex = '';
        el.style.opacity = '';

        var key = self.dragging.key;
        var wasPitch = self.dragging.isPitch;
        var isPitch = self.dragging.overPitch;

        if (self.dragging.moved) {
          if (wasPitch && !isPitch) {
            self.moveToBench(key);
            self.dragging = null;
            self.render();
          } else if (!wasPitch && isPitch) {
            self.moveToPitch(key, self.dragging.x, self.dragging.y);
            self.dragging = null;
            self.render();
            // Show position picker if needed
            self.maybeShowPicker(key);
          } else if (wasPitch && isPitch) {
            self.updatePosition(key, self.dragging.x, self.dragging.y);
            self.dragging = null;
            self.render();
            self.maybeShowPicker(key);
          }
        } else {
          self.dragging = null;
        }
      };

      el.addEventListener('pointerup', finishDrag);
      el.addEventListener('pointercancel', finishDrag);
    });
  },

  // Show position picker if the zone+side has multiple options
  maybeShowPicker: function (key) {
    var pp = null;
    for (var i = 0; i < this.pitch.length; i++) {
      if (this.pitch[i].key === key) { pp = this.pitch[i]; break; }
    }
    if (!pp) return;

    var zone = this.getZone(pp.y);
    var side = this.getSide(pp.x);
    var options = this.getPosOptions(zone, side);

    // For FWD center, check if SS should be added
    if (zone === 'FWD' && side === 'C') {
      var cfCount = 0;
      for (var j = 0; j < this.pitch.length; j++) {
        if (this.pitch[j].key === key) continue;
        var otherPos = this.pitch[j].pos || '';
        if (['CF'].indexOf(otherPos) >= 0) cfCount++;
      }
      // SS is already in options, but only show it if there's another CF
      if (cfCount === 0) {
        options = ['CF']; // remove SS option if no other CF
      }
    }

    if (options.length <= 1) {
      // Auto-assign the single option
      pp.pos = options[0];
      this.render();
      return;
    }

    // Check if current pos is already one of the options
    if (options.indexOf(pp.pos) >= 0) {
      // Current position is valid for this zone, keep it
      return;
    }

    // Show picker
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

    var playerName = ROSTER[key] ? ROSTER[key].name : '';
    picker.innerHTML = '<div class="fe-picker-title">' + playerName + '</div>';

    options.forEach(function (opt) {
      var btn = document.createElement('button');
      btn.className = 'fe-picker-btn';
      btn.textContent = opt;
      btn.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        pp.pos = opt;
        self.removePicker();
        self.render();
      };
      picker.appendChild(btn);
    });

    // Close button
    var closeBtn = document.createElement('button');
    closeBtn.className = 'fe-picker-close';
    closeBtn.textContent = 'X';
    closeBtn.onclick = function (e) {
      e.preventDefault();
      self.removePicker();
      self.render();
    };
    picker.appendChild(closeBtn);

    pitch.appendChild(picker);
    this.pickerEl = picker;
  },

  removePicker: function () {
    if (this.pickerEl) {
      this.pickerEl.remove();
      this.pickerEl = null;
    }
  },

  updatePosition: function (key, x, y) {
    for (var i = 0; i < this.pitch.length; i++) {
      if (this.pitch[i].key === key) {
        this.pitch[i].x = x;
        this.pitch[i].y = y;
        // Auto-calc new position if no picker needed
        var zone = this.getZone(y);
        var side = this.getSide(x);
        var options = this.getPosOptions(zone, side);
        if (options.length === 1) {
          this.pitch[i].pos = options[0];
        }
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
        x: this.pitch[i].x,
        y: this.pitch[i].y,
        pos: this.pitch[i].pos || '',
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
