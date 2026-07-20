/* ===========================================================================
   LINEUP EDITOR v2 — state-based, no DOM juggling
   =========================================================================== */

const LE = {
  state: {},
  bench: [],
  currentFormation: '',
  editMode: false,
  dragging: null,
  freePositions: null,

  init() {
    const params = new URLSearchParams(window.location.search);
    this.currentFormation = params.get('formation') || document.getElementById('formation-select')?.value || '4-3-3';
    this.state = window.__LINEUP__ || {};
    this.bench = window.__BENCH__ || [];
    this.freePositions = window.__FREE_LINEUP__ || null;
    this.render();
  },

  toggleEdit() {
    // Now controlled by the unified Edit button in the template — kept for compatibility
    this.editMode = !this.editMode;
    this.render();
  },

  cancel() {
    window.location.href = '/squad/' + SQUAD_USER_ID;
  },

  render() {
    this.renderPitch();
    this.renderBench();
    if (this.editMode) this.attachDragHandlers();
  },

  renderPitch() {
    const pitch = document.getElementById('pitch');
    if (!pitch) return;
    pitch.innerHTML = '';

    // If we have free positions saved, render using those instead of formation slots
    if (this.freePositions && Object.keys(this.freePositions).length > 0) {
      const label = document.getElementById('formation-label');
      if (label) label.textContent = this.currentFormation.toUpperCase() + ' STARTING XI';
      // Allow overflow so player names/positions aren't clipped
      pitch.style.overflow = 'visible';

      for (const key in this.freePositions) {
        const p = ROSTER[key];
        if (!p) continue;
        const pos = this.freePositions[key];
        const div = document.createElement('div');
        div.className = 'pitch-player';
        div.style.left = (pos.x * 100) + '%';
        div.style.top = (pos.y * 100) + '%';

        const canDrag = this.editMode;
        div.innerHTML =
          '<div class="pitch-link' + (canDrag ? ' draggable' : '') + '" ' +
          (canDrag ? 'draggable="true" data-player="' + key + '" data-slot="free"' : '') + '>' +
          '<img src="' + p.face_url + '" class="pitch-face" alt="">' +
          '<span class="pitch-player-name">' + p.name + '</span>' +
          '<span class="pitch-player-pos">' + (pos.pos || p.pos || '') + '</span>' +
          '</div>';
        pitch.appendChild(div);
      }
      return;
    }

    // Normal formation slot rendering
    const slots = FORMATIONS[this.currentFormation] || [];
    slots.forEach((slot, i) => {
      const playerKey = this.state[i];
      const div = document.createElement('div');
      div.className = 'pitch-player';
      div.style.left = (slot.x * 100) + '%';
      div.style.top = (slot.y * 100) + '%';
      div.dataset.slot = i;

      if (playerKey && ROSTER[playerKey]) {
        const p = ROSTER[playerKey];
        const canDrag = this.editMode;
        div.innerHTML =
          '<div class="pitch-link' + (canDrag ? ' draggable' : '') + '" ' +
          (canDrag ? 'draggable="true"' : '') + ' data-player="' + playerKey + '" data-slot="' + i + '">' +
          '<img src="' + p.face_url + '" class="pitch-face" alt="">' +
          '<span class="pitch-player-name">' + p.name + '</span>' +
          '<span class="pitch-player-pos">' + slot.pos + '</span>' +
          '</div>';
      } else {
        div.innerHTML = '<div class="pitch-empty" data-slot="' + i + '">' + slot.pos + '</div>';
      }
      pitch.appendChild(div);
    });

    const label = document.getElementById('formation-label');
    if (label) label.textContent = this.currentFormation.toUpperCase() + ' STARTING XI';
  },

  renderBench() {
    const benchEl = document.getElementById('bench-list');
    if (!benchEl) return;
    benchEl.innerHTML = '';

    // If free positions exist, filter bench to exclude players on pitch
    let benchKeys = this.bench;
    if (this.freePositions && Object.keys(this.freePositions).length > 0) {
      benchKeys = this.bench.filter(k => !this.freePositions[k]);
    }

    benchKeys.forEach(key => {
      const p = ROSTER[key];
      if (!p) return;
      const canDrag = this.editMode;
      const div = document.createElement('div');
      div.className = 'bench-player' + (canDrag ? ' draggable' : '');
      if (canDrag) div.draggable = true;
      div.dataset.player = key;
      div.dataset.slot = 'bench';
      div.innerHTML =
        '<img src="' + p.face_url + '" class="bench-face" alt="">' +
        '<span class="bench-name">' + p.name + '</span>' +
        '<span class="bench-pos">' + (p.pos || '') + '</span>';
      benchEl.appendChild(div);
    });
  },

  attachDragHandlers() {
    const self = this;

    // dragstart on all draggable elements
    document.querySelectorAll('.draggable').forEach(el => {
      el.addEventListener('dragstart', (e) => {
        self.dragging = {
          player: el.dataset.player,
          from: el.dataset.slot,
        };
        e.dataTransfer.effectAllowed = 'move';
        el.style.opacity = '0.3';
      });
      el.addEventListener('dragend', (e) => {
        el.style.opacity = '';
        document.querySelectorAll('.drag-over').forEach(d => d.classList.remove('drag-over'));
      });
    });

    // pitch slots as drop targets (including empty ones)
    document.querySelectorAll('.pitch-player').forEach(slot => {
      slot.addEventListener('dragover', (e) => {
        e.preventDefault();
        slot.classList.add('drag-over');
      });
      slot.addEventListener('dragleave', () => {
        slot.classList.remove('drag-over');
      });
      slot.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        slot.classList.remove('drag-over');
        if (!self.dragging) return;
        const targetSlot = parseInt(slot.dataset.slot);
        self.moveToSlot(self.dragging.player, self.dragging.from, targetSlot);
        self.dragging = null;
      });
    });

    // Drop OUTSIDE the pitch = bench. Drop on pitch background = cancel.
    document.body.addEventListener('dragover', (e) => {
      const overPitchSlot = e.target.closest('.pitch-player');
      const overPitchArea = e.target.closest('.pitch');
      if (!overPitchSlot && !overPitchArea) {
        e.preventDefault(); // allow drop outside pitch
      }
    });
    document.body.addEventListener('drop', (e) => {
      const overPitchSlot = e.target.closest('.pitch-player');
      const overPitchArea = e.target.closest('.pitch');
      // Only bench if dropped completely OUTSIDE the pitch
      if (!overPitchSlot && !overPitchArea) {
        e.preventDefault();
        e.stopPropagation();
        if (!self.dragging) return;
        self.moveToBench(self.dragging.player, self.dragging.from);
        self.dragging = null;
      }
      // If dropped on pitch area but not on a slot, just cancel (keep player)
    });
  },

  moveToSlot(playerKey, fromSlot, toSlot) {
    if (fromSlot === String(toSlot)) return;

    // Find who's currently in target slot
    const existingKey = this.state[toSlot];

    if (fromSlot === 'bench') {
      // Bench player → pitch slot
      // Remove from bench
      this.bench = this.bench.filter(k => k !== playerKey);
      // If slot was occupied, send that player to bench
      if (existingKey) this.bench.push(existingKey);
      this.state[toSlot] = playerKey;
    } else {
      // Pitch → pitch swap
      const fromIdx = parseInt(fromSlot);
      if (existingKey) {
        this.state[fromIdx] = existingKey;
      } else {
        delete this.state[fromIdx];
      }
      this.state[toSlot] = playerKey;
    }

    this.render();
  },

  moveToBench(playerKey, fromSlot) {
    if (fromSlot === 'bench') return;
    const fromIdx = parseInt(fromSlot);
    delete this.state[fromIdx];
    if (!this.bench.includes(playerKey)) this.bench.push(playerKey);
    this.render();
  },

  async save() {
    const overrides = {};
    Object.keys(this.state).forEach(k => {
      if (this.state[k]) overrides[k] = this.state[k];
    });

    const resp = await fetch('/api/lineup/' + SQUAD_USER_ID, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        formation: this.currentFormation,
        overrides: overrides,
      }),
    });

    if (resp.status === 401) {
      alert('Please log in first.');
      throw new Error('Not logged in');
    }
    if (resp.status === 403) {
      const data = await resp.json();
      throw new Error(data.error || 'Not authorized');
    }

    const data = await resp.json();
    if (!data.ok) {
      throw new Error(data.error || 'Unknown error');
    }
    // Don't reload here — the unified saveAll() in the template handles that
  },
};

// formation dropdown handler (button wiring is done in the template)
document.addEventListener('DOMContentLoaded', () => {
  LE.init();
  const sel = document.getElementById('formation-select');
  if (sel) {
    sel.addEventListener('change', () => {
      if (!LE.editMode) return;
      LE.currentFormation = sel.value;
      // Picking a preset formation abandons any saved free-edit layout,
      // otherwise renderPitch() keeps showing the free positions forever.
      LE.freePositions = null;
      LE.render();
    });
  }
});
