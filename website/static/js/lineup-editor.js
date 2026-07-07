/* ===========================================================================
   LINEUP EDITOR v2 — state-based, no DOM juggling
   =========================================================================== */

const LE = {
  state: {},
  bench: [],
  currentFormation: '',
  editMode: false,
  dragging: null,

  init() {
    const params = new URLSearchParams(window.location.search);
    this.currentFormation = params.get('formation') || document.getElementById('formation-select')?.value || '4-3-3';
    this.state = window.__LINEUP__ || {};
    this.bench = window.__BENCH__ || [];
    this.render();
  },

  toggleEdit() {
    this.editMode = !this.editMode;
    document.getElementById('btn-edit').style.display = this.editMode ? 'none' : '';
    document.getElementById('btn-save').style.display = this.editMode ? '' : 'none';
    document.getElementById('btn-cancel').style.display = this.editMode ? '' : 'none';
    const sel = document.getElementById('formation-select');
    if (sel) sel.disabled = !this.editMode;
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
    const slots = FORMATIONS[this.currentFormation] || [];
    const pitch = document.getElementById('pitch');
    pitch.innerHTML = '';
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
        div.innerHTML = `
          <div class="pitch-link${canDrag ? ' draggable' : ''}" ${canDrag ? 'draggable="true"' : ''} data-player="${playerKey}" data-slot="${i}">
            <img src="${p.face_url}" class="pitch-face" alt="">
            <span class="pitch-player-name">${p.name}</span>
            <span class="pitch-player-pos">${slot.pos}</span>
          </div>`;
      } else {
        div.innerHTML = `<div class="pitch-empty" data-slot="${i}">${slot.pos}</div>`;
      }
      pitch.appendChild(div);
    });

    const label = document.getElementById('formation-label');
    if (label) label.textContent = this.currentFormation.toUpperCase() + ' STARTING XI';
  },

  renderBench() {
    const benchEl = document.getElementById('bench-list');
    benchEl.innerHTML = '';
    this.bench.forEach(key => {
      const p = ROSTER[key];
      if (!p) return;
      const canDrag = this.editMode;
      const div = document.createElement('div');
      div.className = 'bench-player' + (canDrag ? ' draggable' : '');
      if (canDrag) div.draggable = true;
      div.dataset.player = key;
      div.dataset.slot = 'bench';
      div.innerHTML = `
        <img src="${p.face_url}" class="bench-face" alt="">
        <span class="bench-name">${p.name}</span>
        <span class="bench-pos">${p.pos}</span>`;
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

    try {
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
        window.location.href = '/login';
        return;
      }
      if (resp.status === 403) {
        const data = await resp.json();
        alert('Not authorized: ' + (data.error || ''));
        return;
      }

      const data = await resp.json();
      if (data.ok) {
        window.location.href = '/squad/' + SQUAD_USER_ID;
      } else {
        alert('Error: ' + (data.error || 'Unknown'));
      }
    } catch (e) {
      alert('Save failed: ' + e.message);
    }
  },
};

// formation dropdown handler
document.addEventListener('DOMContentLoaded', () => {
  LE.init();
  const sel = document.getElementById('formation-select');
  if (sel) {
    sel.disabled = true;
    sel.addEventListener('change', () => {
      if (!LE.editMode) return;
      LE.currentFormation = sel.value;
      LE.render();
    });
  }
});
