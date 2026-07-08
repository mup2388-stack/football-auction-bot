// ===========================================================================
//  TACTICS EDITOR - FL26 attacking/defensive/advanced instructions
//  Exposes global TC object: init(), enterEdit(), getTactics()
//  Display always renders. Editor opens on enterEdit().
//  Save is handled by the unified saveAll() in the template (sends tactics
//  as part of the lineup POST in one request).
// ===========================================================================

var TC = {
  t: {},
  cfg: {},
  userId: '',

  init: function () {
    this.t = JSON.parse(JSON.stringify(window.__TACTICS__ || {}));
    this.cfg = window.__TACTICS_CONFIG__ || {};
    this.userId = window.SQUAD_USER_ID || '';
    this.renderDisplay();
  },

  getTactics: function () {
    return this.t;
  },

  _label: function (groupKey, value) {
    var arr = this.cfg[groupKey];
    if (!arr) return value;
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].value === value) return arr[i].label;
    }
    return value;
  },

  _desc: function (groupKey, value) {
    var arr = this.cfg[groupKey];
    if (!arr) return '';
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].value === value) return arr[i].desc || '';
    }
    return '';
  },

  // ── DISPLAY (read-only summary, clean and compact) ──
  renderDisplay: function () {
    var el = document.getElementById('tactics-display');
    if (!el) return;
    var t = this.t;
    var self = this;

    var html = '<div class="tac-display-sections">';

    // Attack
    html += '<div class="tac-display-group">';
    html += '<div class="tac-group-label tac-group-attack">Attacking</div>';
    html += this._dRow('Attacking Style', self._label('attack_style', t.attacking_style));
    html += this._dRow('Build-up', self._label('build_up', t.build_up));
    html += this._dRow('Attacking Area', self._label('attack_area', t.attacking_area));
    html += this._dRow('Positioning', self._label('positioning', t.positioning));
    html += this._dSlider('Support Range', t.support_range);
    html += '</div>';

    // Defence
    html += '<div class="tac-display-group">';
    html += '<div class="tac-group-label tac-group-defence">Defensive</div>';
    html += this._dRow('Defensive Style', self._label('defensive_style', t.defensive_style));
    html += this._dRow('Containment', self._label('containment_area', t.containment_area));
    html += this._dRow('Pressuring', self._label('pressuring', t.pressuring));
    html += this._dSlider('Defensive Line', t.defensive_line);
    html += this._dSlider('Compactness', t.compactness);
    html += '</div>';

    // Advanced
    html += '<div class="tac-display-group tac-display-adv">';
    html += '<div class="tac-group-label tac-group-adv">Advanced</div>';
    html += this._dAdv('Atk 1', self._label('adv_attack', t.adv_attack_1));
    html += this._dAdv('Atk 2', self._label('adv_attack', t.adv_attack_2));
    html += this._dAdv('Def 1', self._label('adv_defence', t.adv_defence_1));
    html += this._dAdv('Def 2', self._label('adv_defence', t.adv_defence_2));
    html += '</div>';

    html += '</div>';
    el.innerHTML = html;
  },

  _dRow: function (label, value) {
    return '<div class="tac-d-row"><span>' + label + '</span><strong>' + value + '</strong></div>';
  },

  _dSlider: function (label, value) {
    var pct = (value / 10) * 100;
    return '<div class="tac-d-row"><span>' + label + '</span>' +
      '<span class="tac-d-slider"><span class="tac-d-bar"><span class="tac-d-fill" style="width:' + pct + '%"></span></span>' +
      '<b>' + value + '</b></span></div>';
  },

  _dAdv: function (label, value) {
    var off = value === 'Off' || value === 'off';
    return '<div class="tac-d-row' + (off ? ' tac-d-off' : '') + '"><span>' + label + '</span>' +
      '<strong>' + value + '</strong></div>';
  },

  // ── EDITOR ──
  enterEdit: function () {
    var el = document.getElementById('tactics-editor');
    if (!el) return;
    el.style.display = '';
    el.innerHTML = this._buildEditor();
    this._wireEditor();

    // scroll tactics into view
    var section = document.getElementById('tactics-section');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  _buildEditor: function () {
    var t = this.t;
    var cfg = this.cfg;
    var html = '';

    // Attacking
    html += '<div class="tac-edit-group">';
    html += '<div class="tac-edit-label tac-group-attack">Attacking</div>';
    html += this._selectRow('Attacking Style', 'attacking_style', cfg.attack_style, t.attacking_style);
    html += this._selectRow('Build-up', 'build_up', cfg.build_up, t.build_up);
    html += this._selectRow('Attacking Area', 'attack_area', cfg.attack_area, t.attacking_area);
    html += this._selectRow('Positioning', 'positioning', cfg.positioning, t.positioning);
    html += this._sliderRow('Support Range', 'support_range', t.support_range);
    html += '</div>';

    // Defensive
    html += '<div class="tac-edit-group">';
    html += '<div class="tac-edit-label tac-group-defence">Defensive</div>';
    html += this._selectRow('Defensive Style', 'defensive_style', cfg.defensive_style, t.defensive_style);
    html += this._selectRow('Containment Area', 'containment_area', cfg.containment_area, t.containment_area);
    html += this._selectRow('Pressuring', 'pressuring', cfg.pressuring, t.pressuring);
    html += this._sliderRow('Defensive Line', 'defensive_line', t.defensive_line);
    html += this._sliderRow('Compactness', 'compactness', t.compactness);
    html += '</div>';

    // Advanced
    html += '<div class="tac-edit-group tac-edit-adv">';
    html += '<div class="tac-edit-label tac-group-adv">Advanced Instructions</div>';
    html += '<p class="tac-adv-hint">Pick up to 2 for each side. Use "Off" to leave a slot empty.</p>';
    html += this._selectRow('Attacking 1', 'adv_attack_1', cfg.adv_attack, t.adv_attack_1);
    html += this._selectRow('Attacking 2', 'adv_attack_2', cfg.adv_attack, t.adv_attack_2);
    html += this._selectRow('Defence 1', 'adv_defence_1', cfg.adv_defence, t.adv_defence_1);
    html += this._selectRow('Defence 2', 'adv_defence_2', cfg.adv_defence, t.adv_defence_2);
    html += '</div>';

    return html;
  },

  _selectRow: function (label, key, choices, current) {
    var opts = '';
    for (var i = 0; i < choices.length; i++) {
      var sel = choices[i].value === current ? ' selected' : '';
      opts += '<option value="' + choices[i].value + '"' + sel + '>' + choices[i].label + '</option>';
    }
    return '<div class="tac-field">' +
      '<label class="tac-field-label">' + label + '</label>' +
      '<select class="tac-field-select" data-key="' + key + '">' + opts + '</select>' +
      '<p class="tac-field-desc" data-desc-for="' + key + '"></p>' +
      '</div>';
  },

  _sliderRow: function (label, key, current) {
    var info = this.cfg.sliders ? this.cfg.sliders[key] : null;
    var min = info ? info.min : 1;
    var max = info ? info.max : 10;
    return '<div class="tac-field">' +
      '<label class="tac-field-label">' + label + ' <b class="tac-slider-val" id="' + key + '-val">' + current + '</b></label>' +
      '<input type="range" class="tac-field-range" data-key="' + key + '" min="' + min + '" max="' + max + '" value="' + current + '">' +
      '<p class="tac-field-desc" data-desc-for="' + key + '">' + (info ? info.desc : '') + '</p>' +
      '</div>';
  },

  _wireEditor: function () {
    var self = this;
    var el = document.getElementById('tactics-editor');
    if (!el) return;

    // show description for each field on load + on change
    function updateDesc(key, val) {
      var advMap = {
        'adv_attack_1': 'adv_attack', 'adv_attack_2': 'adv_attack',
        'adv_defence_1': 'adv_defence', 'adv_defence_2': 'adv_defence'
      };
      var groupKey = advMap[key] || key;
      var box = el.querySelector('[data-desc-for="' + key + '"]');
      if (!box) return;
      if (self.cfg.sliders && self.cfg.sliders[key]) {
        box.textContent = self.cfg.sliders[key].desc;
        return;
      }
      box.textContent = self._desc(groupKey, val);
    }

    // init all descriptions
    Object.keys(self.t).forEach(function (key) {
      updateDesc(key, self.t[key]);
    });

    // wire selects
    var selects = el.querySelectorAll('select[data-key]');
    for (var i = 0; i < selects.length; i++) {
      selects[i].addEventListener('change', function () {
        var key = this.getAttribute('data-key');
        self.t[key] = this.value;
        updateDesc(key, this.value);
      });
    }

    // wire sliders
    var sliders = el.querySelectorAll('input[type=range][data-key]');
    for (var j = 0; j < sliders.length; j++) {
      sliders[j].addEventListener('input', function () {
        var key = this.getAttribute('data-key');
        var val = parseInt(this.value);
        self.t[key] = val;
        var valEl = document.getElementById(key + '-val');
        if (valEl) valEl.textContent = val;
      });
    }
  },
};

// Always init display on load
document.addEventListener('DOMContentLoaded', function () {
  TC.init();
});
